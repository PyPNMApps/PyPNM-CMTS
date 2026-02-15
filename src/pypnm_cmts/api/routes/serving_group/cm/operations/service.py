# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
import time

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.config.system_config_settings import SystemConfigSettings
from pypnm.docsis.data_type.sysDescr import SystemDescriptor, SystemDescriptorModel
from pypnm.lib.inet import Inet
from pypnm.lib.ping import Ping
from pypnm.lib.types import (
    InetAddressStr,
    MacAddressStr,
    SnmpCommunity,
    SnmpWriteCommunity,
)

from pypnm_cmts.api.common.service.pnm.asyncio_runner import PnmAsyncioRunner
from pypnm_cmts.api.common.service.pnm.modem import PnmModemResolver
from pypnm_cmts.api.routes.serving_group.cm.operations.schemas import (
    ServingGroupCableModemSysDescrEntryModel,
    ServingGroupCableModemSysDescrGroupModel,
    ServingGroupDocsDevResetNowGroupModel,
    ServingGroupDocsDevResetNowModemModel,
    ServingGroupDocsDevResetNowRequest,
    ServingGroupDocsDevResetNowResponse,
    ServingGroupGetSysDescrResponse,
)
from pypnm_cmts.api.routes.serving_group.operations.service import (
    ServingGroupCacheService,
)
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel
from pypnm_cmts.sgw.runtime_state import (
    get_sgw_manager,
    get_sgw_startup_status,
    get_sgw_store,
)
from pypnm_cmts.sgw.store import SgwCacheStore

SYS_DESCR_OID_NAME = "sysDescr.0"
NO_SYSDESCR_RESPONSES_MESSAGE = "no modem sysDescr responses received"
PARTIAL_FAILURE_MESSAGE = "one or more serving groups returned no modem sysDescr responses"
GET_SYSDESCR_SNMP_TIMEOUT_SECONDS = 3
GET_SYSDESCR_SNMP_RETRIES = 3
DOCS_DEV_RESET_VERIFY_PING_ATTEMPTS = 5
DOCS_DEV_RESET_VERIFY_PING_DELAY_SECONDS = 2.0
DOCS_DEV_RESET_VERIFY_PING_TIMEOUT_SECONDS = 1
NO_RESET_VERIFIED_MESSAGE = "no modem reset verified by ping failure"
PARTIAL_RESET_FAILURE_MESSAGE = "one or more serving groups contain reset verification failures"


class ServingGroupCableModemOperationsService:
    """Service layer for serving-group cable modem operation endpoints."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def docs_dev_reset_now(
        self,
        request: ServingGroupDocsDevResetNowRequest,
    ) -> ServingGroupDocsDevResetNowResponse:
        """Issue docsDevResetNow resets with post-reset ping verification."""
        self.logger.info("docsDevResetNow [START]")
        status = get_sgw_startup_status()
        if not bool(status.startup_completed):
            self.logger.warning("docsDevResetNow [ABORT] reason=sgw startup not completed")
            return self._build_docs_dev_reset_failure("sgw startup not completed")
        if not bool(status.discovery_ok) or bool(status.prime_failed):
            message = status.error_message if status.error_message != "" else "sgw startup failed"
            self.logger.warning("docsDevResetNow [ABORT] reason=%s", message)
            return self._build_docs_dev_reset_failure(message)

        store = get_sgw_store()
        if store is None:
            self.logger.warning("docsDevResetNow [ABORT] reason=sgw store not available")
            return self._build_docs_dev_reset_failure(ServingGroupCacheService.STORE_UNAVAILABLE_MESSAGE)
        manager = get_sgw_manager()
        if manager is None:
            self.logger.warning("docsDevResetNow [ABORT] reason=sgw manager not available")
            return self._build_docs_dev_reset_failure("sgw manager not available")

        discovered_sg_ids = list(status.discovered_sg_ids)
        requested_sg_ids = list(request.cmts.serving_group.id)
        requested_mac_addresses = list(request.cmts.cable_modem.mac_address)
        selected_macs = set(requested_mac_addresses)
        resolved_sg_ids, missing_sg_ids = self._resolve_sg_scope(requested_sg_ids, discovered_sg_ids)
        scoped_modems = self._resolve_scoped_modems(store, resolved_sg_ids, requested_mac_addresses)
        resolved_mac_addresses = [scoped_mac for _scoped_sg, scoped_mac, _scoped_ip in scoped_modems]
        missing_mac_addresses = self._resolve_missing_mac_scope(requested_mac_addresses, resolved_mac_addresses)
        write_community = self._resolve_write_community(request)

        self.logger.info(
            "docsDevResetNow [SCOPE] requested_sg_ids=%s resolved_sg_count=%d requested_mac_count=%d resolved_modem_count=%d",
            requested_sg_ids,
            len(resolved_sg_ids),
            len(requested_mac_addresses),
            len(scoped_modems),
        )

        per_sg_results = manager.run_scoped_job(
            sg_ids=resolved_sg_ids,
            worker=lambda sg_id: self._collect_docs_dev_reset_for_sg(
                store=store,
                sg_id=sg_id,
                selected_macs=selected_macs,
                write_community=write_community,
            ),
        )

        groups: list[ServingGroupDocsDevResetNowGroupModel] = []
        for sg_id in resolved_sg_ids:
            group_result = per_sg_results.get(
                sg_id,
                ServingGroupDocsDevResetNowGroupModel(
                    sg_id=sg_id,
                    status=ServiceStatusCode.FAILURE,
                    message="sgw scoped worker did not return result",
                    modem_count=0,
                    success_count=0,
                    failure_count=0,
                    modems={},
                ),
            )
            groups.append(group_result)

        endpoint_status = ServiceStatusCode.SUCCESS
        endpoint_message = ""
        total_modems = sum(group.modem_count for group in groups)
        total_success = sum(group.success_count for group in groups)
        failed_groups = [group for group in groups if group.status != ServiceStatusCode.SUCCESS]
        if requested_mac_addresses and missing_mac_addresses:
            endpoint_status = ServiceStatusCode.FAILURE
            endpoint_message = f"mac_address not found in resolved scope: {missing_mac_addresses[0]}"
        elif requested_sg_ids and missing_sg_ids:
            endpoint_status = ServiceStatusCode.FAILURE
            endpoint_message = ServingGroupCacheService.SG_NOT_FOUND_TEMPLATE.format(sg_id=int(missing_sg_ids[0]))
        elif not groups:
            endpoint_message = ServingGroupCacheService.NO_DISCOVERED_MESSAGE
        elif total_modems > 0 and total_success == 0:
            endpoint_status = ServiceStatusCode.FAILURE
            endpoint_message = NO_RESET_VERIFIED_MESSAGE
        elif failed_groups:
            endpoint_message = PARTIAL_RESET_FAILURE_MESSAGE

        self.logger.info(
            "docsDevResetNow [COMPLETE] groups=%d total_modems=%d total_success=%d",
            len(groups),
            total_modems,
            total_success,
        )

        return ServingGroupDocsDevResetNowResponse(
            status=endpoint_status,
            message=endpoint_message,
            timestamp=ServingGroupCacheService._utc_now(),
            requested_sg_ids=requested_sg_ids,
            requested_mac_addresses=requested_mac_addresses,
            resolved_sg_ids=resolved_sg_ids,
            missing_sg_ids=missing_sg_ids,
            missing_mac_addresses=missing_mac_addresses,
            groups=groups,
        )

    def get_sys_descr(
        self,
        request: ServingGroupDocsDevResetNowRequest,
    ) -> ServingGroupGetSysDescrResponse:
        """Collect per-modem sysDescr and return per-SG grouped response."""
        self.logger.info("getSysDescr [START]")
        status = get_sgw_startup_status()
        if not bool(status.startup_completed):
            self.logger.warning("getSysDescr [ABORT] reason=sgw startup not completed")
            return self._build_sys_descr_failure("sgw startup not completed")
        if not bool(status.discovery_ok) or bool(status.prime_failed):
            message = status.error_message if status.error_message != "" else "sgw startup failed"
            self.logger.warning("getSysDescr [ABORT] reason=%s", message)
            return self._build_sys_descr_failure(message)

        store = get_sgw_store()
        if store is None:
            self.logger.warning("getSysDescr [ABORT] reason=sgw store not available")
            return self._build_sys_descr_failure(ServingGroupCacheService.STORE_UNAVAILABLE_MESSAGE)

        manager = get_sgw_manager()
        if manager is None:
            self.logger.warning("getSysDescr [ABORT] reason=sgw manager not available")
            return self._build_sys_descr_failure("sgw manager not available")

        discovered_sg_ids = list(status.discovered_sg_ids)
        requested_sg_ids = list(request.cmts.serving_group.id)
        requested_mac_addresses = list(request.cmts.cable_modem.mac_address)
        selected_macs = set(requested_mac_addresses)
        resolved_sg_ids, missing_sg_ids = self._resolve_sg_scope(requested_sg_ids, discovered_sg_ids)
        scoped_modems = self._resolve_scoped_modems(store, resolved_sg_ids, requested_mac_addresses)
        resolved_mac_addresses = [scoped_mac for _scoped_sg, scoped_mac, _scoped_ip in scoped_modems]
        missing_mac_addresses = self._resolve_missing_mac_scope(requested_mac_addresses, resolved_mac_addresses)

        communities = self._resolve_sys_descr_communities(request)
        self.logger.info(
            "getSysDescr [SCOPE] requested_sg_ids=%s resolved_sg_count=%d requested_mac_count=%d resolved_modem_count=%d",
            requested_sg_ids,
            len(resolved_sg_ids),
            len(requested_mac_addresses),
            len(scoped_modems),
        )
        self.logger.info(
            "getSysDescr [COMMUNITIES] count=%d values=%s",
            len(communities),
            [str(community) for community in communities],
        )

        per_sg_results = manager.run_scoped_job(
            sg_ids=resolved_sg_ids,
            worker=lambda sg_id: self._collect_sys_descr_for_sg(
                store=store,
                sg_id=sg_id,
                selected_macs=selected_macs,
                communities=communities,
            ),
        )

        groups: list[ServingGroupCableModemSysDescrGroupModel] = []
        for sg_id in resolved_sg_ids:
            group_result = per_sg_results.get(
                sg_id,
                ServingGroupCableModemSysDescrGroupModel(
                    sg_id=sg_id,
                    status=ServiceStatusCode.FAILURE,
                    message="sgw scoped worker did not return result",
                    modem_count=0,
                    success_count=0,
                    failure_count=0,
                    modems={},
                ),
            )
            groups.append(group_result)

        endpoint_status = ServiceStatusCode.SUCCESS
        endpoint_message = ""
        total_modems = sum(group.modem_count for group in groups)
        total_success = sum(group.success_count for group in groups)
        failed_groups = [group for group in groups if group.status != ServiceStatusCode.SUCCESS]

        if not groups:
            endpoint_message = ServingGroupCacheService.NO_DISCOVERED_MESSAGE
            if requested_sg_ids or requested_mac_addresses:
                endpoint_status = ServiceStatusCode.FAILURE
                if requested_mac_addresses and missing_mac_addresses:
                    endpoint_message = f"mac_address not found in resolved scope: {missing_mac_addresses[0]}"
                elif requested_sg_ids and missing_sg_ids:
                    endpoint_message = ServingGroupCacheService.SG_NOT_FOUND_TEMPLATE.format(sg_id=int(missing_sg_ids[0]))
        elif total_modems > 0 and total_success == 0:
            endpoint_status = ServiceStatusCode.FAILURE
            endpoint_message = NO_SYSDESCR_RESPONSES_MESSAGE
        elif failed_groups:
            endpoint_message = PARTIAL_FAILURE_MESSAGE

        self.logger.info("getSysDescr [COMPLETE] groups=%d total_modems=%d total_success=%d", len(groups), total_modems, total_success)

        return ServingGroupGetSysDescrResponse(
            status=endpoint_status,
            message=endpoint_message,
            timestamp=ServingGroupCacheService._utc_now(),
            requested_sg_ids=requested_sg_ids,
            requested_mac_addresses=requested_mac_addresses,
            resolved_sg_ids=resolved_sg_ids,
            missing_sg_ids=missing_sg_ids,
            missing_mac_addresses=missing_mac_addresses,
            groups=groups,
        )

    def _build_docs_dev_reset_failure(self, message: str) -> ServingGroupDocsDevResetNowResponse:
        return ServingGroupDocsDevResetNowResponse(
            status=ServiceStatusCode.FAILURE,
            message=message,
            timestamp=ServingGroupCacheService._utc_now(),
            requested_sg_ids=[],
            requested_mac_addresses=[],
            resolved_sg_ids=[],
            missing_sg_ids=[],
            missing_mac_addresses=[],
            groups=[],
        )

    def _build_sys_descr_failure(self, message: str) -> ServingGroupGetSysDescrResponse:
        return ServingGroupGetSysDescrResponse(
            status=ServiceStatusCode.FAILURE,
            message=message,
            timestamp=ServingGroupCacheService._utc_now(),
            requested_sg_ids=[],
            requested_mac_addresses=[],
            resolved_sg_ids=[],
            missing_sg_ids=[],
            missing_mac_addresses=[],
            groups=[],
        )

    @staticmethod
    def _resolve_sg_scope(
        requested_sg_ids: list[ServiceGroupId],
        discovered_sg_ids: list[ServiceGroupId],
    ) -> tuple[list[ServiceGroupId], list[ServiceGroupId]]:
        if not requested_sg_ids:
            return (list(discovered_sg_ids), [])
        resolved_sg_ids = [sg_id for sg_id in requested_sg_ids if sg_id in discovered_sg_ids]
        missing_sg_ids = [sg_id for sg_id in requested_sg_ids if sg_id not in discovered_sg_ids]
        return (resolved_sg_ids, missing_sg_ids)

    def _resolve_scoped_modems(
        self,
        store: SgwCacheStore,
        resolved_sg_ids: list[ServiceGroupId],
        requested_mac_addresses: list[MacAddressStr],
    ) -> list[tuple[ServiceGroupId, MacAddressStr, InetAddressStr | None]]:
        scoped: list[tuple[ServiceGroupId, MacAddressStr, InetAddressStr | None]] = []
        selected_macs = set(requested_mac_addresses)
        for sg_id in resolved_sg_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                continue
            ordered_modems = ServingGroupCacheService._sort_modems(list(entry.snapshot.cable_modems))
            for modem in ordered_modems:
                modem_mac = MacAddressStr(str(modem.mac))
                if selected_macs and modem_mac not in selected_macs:
                    continue
                modem_ip = self._normalize_modem_ip(modem)
                scoped.append((sg_id, modem_mac, modem_ip))
        return scoped

    @staticmethod
    def _resolve_missing_mac_scope(
        requested_mac_addresses: list[MacAddressStr],
        resolved_mac_addresses: list[MacAddressStr],
    ) -> list[MacAddressStr]:
        if not requested_mac_addresses:
            return []
        resolved_set = set(resolved_mac_addresses)
        return [mac_address for mac_address in requested_mac_addresses if mac_address not in resolved_set]

    @staticmethod
    def _normalize_modem_ip(modem: SgwCableModemModel) -> InetAddressStr | None:
        ip_value = PnmModemResolver.select_ip(modem)
        if ip_value is None:
            return None
        try:
            return InetAddressStr(str(Inet(ip_value)))
        except Exception:
            return None

    @staticmethod
    def _resolve_write_community(request: ServingGroupDocsDevResetNowRequest) -> SnmpWriteCommunity:
        snmp = request.cmts.cable_modem.snmp
        snmp_v2c = snmp.snmpV2C if snmp is not None else None
        community = snmp_v2c.community if snmp_v2c is not None else None
        if community is not None:
            return community
        return SnmpWriteCommunity(PnmConfigManager.get_write_community())

    @staticmethod
    def _send_docs_dev_reset_now(
        mac_address: MacAddressStr,
        ip_address: InetAddressStr,
        write_community: SnmpWriteCommunity,
    ) -> tuple[ServiceStatusCode, str]:
        try:
            cable_modem = PnmModemResolver.build_cable_modem(
                mac_address=mac_address,
                ip_address=ip_address,
                write_community=str(write_community),
            )
            reset_ok = PnmAsyncioRunner.run_on_isolated_event_loop(cable_modem.setDocsDevResetNow())
        except Exception as exc:
            return (ServiceStatusCode.FAILURE, f"docsDevResetNow exception: {exc}")
        if not bool(reset_ok):
            return (ServiceStatusCode.RESET_NOW_FAILED, "docsDevResetNow returned false")
        return (ServiceStatusCode.SUCCESS, "docsDevResetNow command sent")

    def _collect_docs_dev_reset_for_sg(
        self,
        store: SgwCacheStore,
        sg_id: ServiceGroupId,
        selected_macs: set[MacAddressStr],
        write_community: SnmpWriteCommunity,
    ) -> ServingGroupDocsDevResetNowGroupModel:
        entries: dict[MacAddressStr, ServingGroupDocsDevResetNowModemModel] = {}
        cache_entry = store.get_entry(sg_id)
        if cache_entry is None:
            return ServingGroupDocsDevResetNowGroupModel(
                sg_id=sg_id,
                status=ServiceStatusCode.FAILURE,
                message="sg entry missing in cache",
                modem_count=0,
                success_count=0,
                failure_count=0,
                modems={},
            )

        ordered_modems = ServingGroupCacheService._sort_modems(list(cache_entry.snapshot.cable_modems))
        modem_count = 0
        success_count = 0
        failure_count = 0
        for modem in ordered_modems:
            modem_mac = MacAddressStr(str(modem.mac))
            if selected_macs and modem_mac not in selected_macs:
                continue
            modem_count += 1
            entries[modem_mac] = self._execute_docs_dev_reset_for_modem(
                sg_id=sg_id,
                mac_address=modem_mac,
                ip_address=self._normalize_modem_ip(modem),
                write_community=write_community,
            )
            if entries[modem_mac].status == ServiceStatusCode.SUCCESS:
                success_count += 1
            else:
                failure_count += 1

        group_status = ServiceStatusCode.SUCCESS
        group_message = ""
        if modem_count > 0 and success_count == 0:
            group_status = ServiceStatusCode.FAILURE
            group_message = NO_RESET_VERIFIED_MESSAGE

        return ServingGroupDocsDevResetNowGroupModel(
            sg_id=sg_id,
            status=group_status,
            message=group_message,
            modem_count=modem_count,
            success_count=success_count,
            failure_count=failure_count,
            modems=entries,
        )

    def _execute_docs_dev_reset_for_modem(
        self,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
        ip_address: InetAddressStr | None,
        write_community: SnmpWriteCommunity,
    ) -> ServingGroupDocsDevResetNowModemModel:
        if ip_address is None:
            return ServingGroupDocsDevResetNowModemModel(
                ip_address=None,
                status=ServiceStatusCode.FAILURE,
                message="unable to resolve modem IP address",
            )

        reset_status, reset_message = self._send_docs_dev_reset_now(
            mac_address=mac_address,
            ip_address=ip_address,
            write_community=write_community,
        )
        if reset_status != ServiceStatusCode.SUCCESS:
            return ServingGroupDocsDevResetNowModemModel(
                ip_address=ip_address,
                status=reset_status,
                message=reset_message,
            )

        verify_status, verify_message, ping_attempts, ping_last_reachable = self._verify_docs_dev_reset_ping_failure(
            sg_id=sg_id,
            mac_address=mac_address,
            ip_address=ip_address,
            write_community=write_community,
        )
        return ServingGroupDocsDevResetNowModemModel(
            ip_address=ip_address,
            status=verify_status,
            message=verify_message,
            ping_attempts=ping_attempts,
            ping_last_reachable=ping_last_reachable,
        )

    def _verify_docs_dev_reset_ping_failure(
        self,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
        ip_address: InetAddressStr,
        write_community: SnmpWriteCommunity,
    ) -> tuple[ServiceStatusCode, str, int, bool]:
        for attempt in range(1, DOCS_DEV_RESET_VERIFY_PING_ATTEMPTS + 1):
            reachable = self._is_modem_ping_reachable(
                mac_address=mac_address,
                ip_address=ip_address,
                write_community=write_community,
            )
            self.logger.info(
                "docsDevResetNow [PING_VERIFY] sg_id=%s mac=%s inet=%s attempt=%d/%d reachable=%s",
                sg_id,
                mac_address,
                ip_address,
                attempt,
                DOCS_DEV_RESET_VERIFY_PING_ATTEMPTS,
                reachable,
            )
            if not reachable:
                return (
                    ServiceStatusCode.SUCCESS,
                    f"docsDevResetNow verified by ping failure after {attempt} attempt(s)",
                    attempt,
                    False,
                )
            if attempt < DOCS_DEV_RESET_VERIFY_PING_ATTEMPTS:
                self._sleep_before_ping_retry()

        return (
            ServiceStatusCode.PING_FAILED,
            "docsDevResetNow verification failed: modem still ping reachable after retries",
            DOCS_DEV_RESET_VERIFY_PING_ATTEMPTS,
            True,
        )

    @staticmethod
    def _is_modem_ping_reachable(
        mac_address: MacAddressStr,
        ip_address: InetAddressStr,
        write_community: SnmpWriteCommunity,
    ) -> bool:
        cable_modem = PnmModemResolver.build_cable_modem(
            mac_address=mac_address,
            ip_address=ip_address,
            write_community=str(write_community),
        )
        try:
            return bool(cable_modem.is_ping_reachable())
        except Exception:
            return bool(Ping.is_reachable(str(ip_address), timeout=DOCS_DEV_RESET_VERIFY_PING_TIMEOUT_SECONDS, count=1))

    @staticmethod
    def _sleep_before_ping_retry() -> None:
        time.sleep(DOCS_DEV_RESET_VERIFY_PING_DELAY_SECONDS)

    def _collect_sys_descr_for_sg(
        self,
        store: SgwCacheStore,
        sg_id: ServiceGroupId,
        selected_macs: set[MacAddressStr],
        communities: list[SnmpCommunity],
    ) -> ServingGroupCableModemSysDescrGroupModel:
        entries: dict[MacAddressStr, ServingGroupCableModemSysDescrEntryModel] = {}
        cache_entry = store.get_entry(sg_id)
        if cache_entry is None:
            return ServingGroupCableModemSysDescrGroupModel(
                sg_id=sg_id,
                status=ServiceStatusCode.FAILURE,
                message="sg entry missing in cache",
                modem_count=0,
                success_count=0,
                failure_count=0,
                modems={},
            )

        ordered_modems = ServingGroupCacheService._sort_modems(list(cache_entry.snapshot.cable_modems))
        modem_count = 0
        success_count = 0
        failure_count = 0
        for modem in ordered_modems:
            modem_mac = MacAddressStr(str(modem.mac))
            if selected_macs and modem_mac not in selected_macs:
                continue
            modem_count += 1

            modem_ip = self._normalize_modem_ip(modem)
            if modem_ip is None:
                failure_count += 1
                entries[modem_mac] = ServingGroupCableModemSysDescrEntryModel(sysdescr=SystemDescriptor.empty().to_model())
                continue

            sysdescr_model = self._collect_modem_sysdescr(
                sg_id=sg_id,
                mac_address=modem_mac,
                ip_address=modem_ip,
                communities=communities,
            )
            if sysdescr_model is None:
                entries[modem_mac] = ServingGroupCableModemSysDescrEntryModel(sysdescr=SystemDescriptor.empty().to_model())
                failure_count += 1
            else:
                entries[modem_mac] = ServingGroupCableModemSysDescrEntryModel(sysdescr=sysdescr_model)
                success_count += 1

        group_status = ServiceStatusCode.SUCCESS
        group_message = ""
        if modem_count > 0 and success_count == 0:
            group_status = ServiceStatusCode.FAILURE
            group_message = NO_SYSDESCR_RESPONSES_MESSAGE

        return ServingGroupCableModemSysDescrGroupModel(
            sg_id=sg_id,
            status=group_status,
            message=group_message,
            modem_count=modem_count,
            success_count=success_count,
            failure_count=failure_count,
            modems=entries,
        )

    @staticmethod
    def _collect_modem_sysdescr(
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
        ip_address: InetAddressStr,
        communities: list[SnmpCommunity],
    ) -> SystemDescriptorModel | None:
        logger = logging.getLogger(ServingGroupCableModemOperationsService.__name__)
        for community in communities:
            current_oid_name = SYS_DESCR_OID_NAME
            try:
                logger.info(
                    "getSysDescr [POLL_ATTEMPT] sg_id=%s mac=%s inet=%s community=%s oid=%s outcome=attempt",
                    sg_id,
                    mac_address,
                    ip_address,
                    str(community),
                    SYS_DESCR_OID_NAME,
                )
                cable_modem = PnmModemResolver.build_cable_modem(
                    mac_address=mac_address,
                    ip_address=ip_address,
                    write_community=str(community),
                )
                sysdescr_model = PnmAsyncioRunner.run_on_isolated_event_loop(
                    cable_modem.getSysDescr(
                        timeout=GET_SYSDESCR_SNMP_TIMEOUT_SECONDS,
                        retries=GET_SYSDESCR_SNMP_RETRIES,
                    )
                )
                sysdescr_text = str(sysdescr_model).strip()
                if sysdescr_text == "":
                    logger.info(
                        "getSysDescr [POLL_RESULT] sg_id=%s mac=%s inet=%s community=%s oid=%s outcome=empty",
                        sg_id,
                        mac_address,
                        ip_address,
                        str(community),
                        SYS_DESCR_OID_NAME,
                    )
                    continue
                logger.info(
                    "getSysDescr [POLL_RESULT] sg_id=%s mac=%s inet=%s community=%s oid=%s outcome=success",
                    sg_id,
                    mac_address,
                    ip_address,
                    str(community),
                    SYS_DESCR_OID_NAME,
                )
                return sysdescr_model.to_model()
            except Exception as exc:
                logger.warning(
                    "getSysDescr [POLL_RESULT] sg_id=%s mac=%s inet=%s community=%s oid=%s outcome=exception error=%s",
                    sg_id,
                    mac_address,
                    ip_address,
                    str(community),
                    current_oid_name,
                    exc,
                )
                continue
        return None

    @staticmethod
    def _resolve_sys_descr_communities(request: ServingGroupDocsDevResetNowRequest) -> list[SnmpCommunity]:
        snmp = request.cmts.cable_modem.snmp
        snmp_v2c = snmp.snmpV2C if snmp is not None else None
        request_community = snmp_v2c.community if snmp_v2c is not None else None
        if request_community is not None:
            value = str(request_community).strip()
            if value != "":
                return [SnmpCommunity(value)]

        try:
            settings = CmtsOrchestratorSettings.from_system_config()
            adapter_community = str(settings.adapter.community).strip()
            if adapter_community != "":
                return [SnmpCommunity(adapter_community)]
        except Exception:
            pass

        read_community = str(SystemConfigSettings.snmp_read_community()).strip()
        if read_community != "":
            return [SnmpCommunity(read_community)]
        return []

__all__ = [
    "ServingGroupCableModemOperationsService",
]

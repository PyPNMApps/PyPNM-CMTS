# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.lib.inet import Inet
from pypnm.lib.types import InetAddressStr, MacAddressStr, SnmpWriteCommunity

from pypnm_cmts.api.common.service.pnm.asyncio_runner import PnmAsyncioRunner
from pypnm_cmts.api.common.service.pnm.modem import PnmModemResolver
from pypnm_cmts.api.routes.serving_group.cm.operations.schemas import (
    ServingGroupDocsDevResetNowRequest,
    ServingGroupDocsDevResetNowResponse,
    ServingGroupDocsDevResetNowResultModel,
)
from pypnm_cmts.api.routes.serving_group.operations.service import (
    ServingGroupCacheService,
)
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel
from pypnm_cmts.sgw.runtime_state import get_sgw_startup_status, get_sgw_store
from pypnm_cmts.sgw.store import SgwCacheStore


class ServingGroupCableModemOperationsService:
    """Service layer for serving-group cable modem operation endpoints."""

    def docs_dev_reset_now(
        self,
        request: ServingGroupDocsDevResetNowRequest,
    ) -> ServingGroupDocsDevResetNowResponse:
        """Issue docsDevResetNow resets for resolved SG-scoped cable modems."""
        status = get_sgw_startup_status()
        if not bool(status.startup_completed):
            return self._build_docs_dev_reset_failure("sgw startup not completed")
        if not bool(status.discovery_ok) or bool(status.prime_failed):
            message = status.error_message if status.error_message != "" else "sgw startup failed"
            return self._build_docs_dev_reset_failure(message)

        store = get_sgw_store()
        if store is None:
            return self._build_docs_dev_reset_failure(ServingGroupCacheService.STORE_UNAVAILABLE_MESSAGE)

        discovered_sg_ids = list(status.discovered_sg_ids)
        requested_sg_ids = list(request.cmts.serving_group.id)
        requested_mac_addresses = list(request.cmts.cable_modem.mac_address)
        resolved_sg_ids, missing_sg_ids = self._resolve_sg_scope(requested_sg_ids, discovered_sg_ids)
        scoped_modems = self._resolve_scoped_modems(store, resolved_sg_ids, requested_mac_addresses)
        resolved_mac_addresses = [scoped_mac for _scoped_sg, scoped_mac, _scoped_ip in scoped_modems]
        missing_mac_addresses = self._resolve_missing_mac_scope(requested_mac_addresses, resolved_mac_addresses)
        write_community = self._resolve_write_community(request)

        results: list[ServingGroupDocsDevResetNowResultModel] = []
        success_count = 0
        failure_count = 0
        for sg_id, mac_address, ip_address in scoped_modems:
            if ip_address is None:
                failure_count += 1
                results.append(
                    ServingGroupDocsDevResetNowResultModel(
                        sg_id=sg_id,
                        mac_address=mac_address,
                        ip_address=None,
                        status=ServiceStatusCode.FAILURE,
                        message="unable to resolve modem IP address",
                    )
                )
                continue

            reset_status, reset_message = self._send_docs_dev_reset_now(
                mac_address=mac_address,
                ip_address=ip_address,
                write_community=write_community,
            )
            if reset_status == ServiceStatusCode.SUCCESS:
                success_count += 1
            else:
                failure_count += 1
            results.append(
                ServingGroupDocsDevResetNowResultModel(
                    sg_id=sg_id,
                    mac_address=mac_address,
                    ip_address=ip_address,
                    status=reset_status,
                    message=reset_message,
                )
            )

        attempted_count = len(scoped_modems)
        response_status = ServiceStatusCode.SUCCESS
        message = ""
        if attempted_count == 0:
            message = ServingGroupCacheService.NO_DISCOVERED_MESSAGE
            if requested_sg_ids or requested_mac_addresses:
                response_status = ServiceStatusCode.FAILURE
                if requested_mac_addresses and missing_mac_addresses:
                    message = f"mac_address not found in resolved scope: {missing_mac_addresses[0]}"
                elif requested_sg_ids and missing_sg_ids:
                    message = ServingGroupCacheService.SG_NOT_FOUND_TEMPLATE.format(sg_id=int(missing_sg_ids[0]))
        elif failure_count > 0:
            response_status = ServiceStatusCode.FAILURE
            message = "one or more reset commands failed"

        return ServingGroupDocsDevResetNowResponse(
            status=response_status,
            message=message,
            timestamp=ServingGroupCacheService._utc_now(),
            requested_sg_ids=requested_sg_ids,
            requested_mac_addresses=requested_mac_addresses,
            resolved_sg_ids=resolved_sg_ids,
            resolved_mac_addresses=resolved_mac_addresses,
            missing_sg_ids=missing_sg_ids,
            missing_mac_addresses=missing_mac_addresses,
            attempted_count=attempted_count,
            success_count=success_count,
            failure_count=failure_count,
            results=results,
        )

    def _build_docs_dev_reset_failure(self, message: str) -> ServingGroupDocsDevResetNowResponse:
        return ServingGroupDocsDevResetNowResponse(
            status=ServiceStatusCode.FAILURE,
            message=message,
            timestamp=ServingGroupCacheService._utc_now(),
            requested_sg_ids=[],
            requested_mac_addresses=[],
            resolved_sg_ids=[],
            resolved_mac_addresses=[],
            missing_sg_ids=[],
            missing_mac_addresses=[],
            attempted_count=0,
            success_count=0,
            failure_count=0,
            results=[],
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


__all__ = [
    "ServingGroupCableModemOperationsService",
]

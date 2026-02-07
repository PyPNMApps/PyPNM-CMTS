## Agent Review Bundle Summary
- Goal: Log resolved SNMP community value during RxMER precheck for troubleshooting.
- Changes: Added  to the RxMER precheck-start log line and passed resolved write community value.
- Files: src/pypnm_cmts/api/routes/pnm/sg/ds/ofdm/rxmer/service.py
- Tests: ruff check src/pypnm_cmts/api/routes/pnm/sg/ds/ofdm/rxmer/service.py; pytest -q tests/test_rxmer_orchestration.py tests/test_rxmer_pnm_artifacts.py
- Notes: Community string is now visible in logs for both request override and system default paths.

# FILE: src/pypnm_cmts/api/routes/pnm/sg/ds/ofdm/rxmer/service.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import ipaddress
import logging
from collections.abc import Callable
from contextlib import suppress

from pypnm.api.routes.common.classes.operation.cable_modem_precheck import (
    CableModemServicePreCheck,
)
from pypnm.api.routes.common.extended.common_measure_schema import (
    DownstreamOfdmParameters,
)
from pypnm.api.routes.common.extended.common_messaging_service import (
    MessagePayload,
    MessageResponse,
    MessageResponseType,
)
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.api.routes.docs.pnm.ds.ofdm.rxmer.service import CmDsOfdmRxMerService
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.docsis.cable_modem import CableModem
from pypnm.lib.inet import Inet
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import (
    ChannelId,
    FileNameStr,
    InetAddressStr,
    MacAddressStr,
    TimestampSec,
    TransactionId,
)
from pypnm.lib.utils import Generate, TimeUnit

from pypnm_cmts.api.common.cmts_request import CmtsRequestEnvelopeModel
from pypnm_cmts.api.common.operations.models import (
    OperationExecutionModel,
    OperationRequestContextModel,
    OperationRequestSummaryModel,
    OperationResultsSummaryModel,
    OperationStageResultModel,
)
from pypnm_cmts.api.common.operations.runner import (
    OperationRunner,
    OperationWorkerResultModel,
    OperationWorkItemModel,
)
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.schemas import (
    RxMerServiceGroupCancelResponse,
    RxMerServiceGroupOperationRequest,
    RxMerServiceGroupResultsResponse,
    RxMerServiceGroupStartCaptureRequest,
    RxMerServiceGroupStartCaptureResponse,
    RxMerServiceGroupStatusResponse,
)
from pypnm_cmts.lib.constants import OperationStage, OperationState
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel
from pypnm_cmts.sgw.runtime_state import get_sgw_store
from pypnm_cmts.sgw.store import SgwCacheStore

DEFAULT_MAX_INLINE_RECORDS = 250
NOT_FOUND_MESSAGE = "operation not found"
CLEAR_MESSAGE = ""
PRECHECK_FAILURE_MESSAGE = "precheck failed"
MISSING_IP_MESSAGE = "modem ip address missing"
NO_MESSAGE_RESPONSE = "capture returned no message response"
MISSING_TRANSACTION_MESSAGE = "missing transaction_id or filename"

CaptureExecutor = Callable[
    [CableModem, DownstreamOfdmParameters | None, tuple[Inet, Inet], str],
    MessageResponse,
]
PrecheckExecutor = Callable[[CableModem], tuple[ServiceStatusCode, str]]


class RxMerCaptureWorker:
    """Execute eligibility, precheck, and capture stages for a single modem."""

    def __init__(
        self,
        store: OperationStore,
        capture_executor: CaptureExecutor,
        precheck_executor: PrecheckExecutor,
        sgw_store: SgwCacheStore | None,
    ) -> None:
        self._store = store
        self._capture_executor = capture_executor
        self._precheck_executor = precheck_executor
        self._sgw_store = sgw_store
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def __call__(self, item: OperationWorkItemModel) -> OperationWorkerResultModel:
        """Run eligibility, precheck, and capture for a modem work item."""
        self.logger.info(
            "RxMER-Worker [START] operation_id=%s, sg_id=%s, mac=%s, attempt=%s",
            item.operation_id,
            item.sg_id,
            item.mac_address,
            item.attempt,
        )
        state = self._store.load_state(item.operation_id)
        request_summary = state.request_summary
        request_context = self._store.load_request_context(item.operation_id)
        ip_address = self._resolve_modem_ip(item.sg_id, item.mac_address)
        now_epoch = self._now_epoch()
        stages: list[OperationStageResultModel] = []
        eligibility_result = OperationStageResultModel(
            stage=OperationStage.ELIGIBILITY,
            status_code=ServiceStatusCode.SUCCESS if ip_address is not None else ServiceStatusCode.INVALID_CAPTURE_PARAMETERS,
            transaction_ids=[],
            filenames=[],
            message="" if ip_address is not None else MISSING_IP_MESSAGE,
            started_epoch=now_epoch,
            finished_epoch=now_epoch,
        )
        stages.append(eligibility_result)
        if eligibility_result.status_code != ServiceStatusCode.SUCCESS:
            self.logger.info(
                "rxmer worker eligibility_failed operation_id=%s sg_id=%s mac=%s status=%s message=%s",
                item.operation_id,
                item.sg_id,
                item.mac_address,
                eligibility_result.status_code.value,
                eligibility_result.message,
            )
            return OperationWorkerResultModel(ip_address=ip_address, stages=stages)

        write_community = self._resolve_write_community(request_context)
        community_source = "request_override"
        if request_context is None or request_context.snmp_write_community is None:
            community_source = "system_default"
        cm = CableModem(
            mac_address=MacAddress(item.mac_address),
            inet=Inet(InetAddressStr(ip_address)),
            write_community=write_community,
        )
        self.logger.info(
            "RxMER-Worker [PRECHECK_START] operation_id=%s sg_id=%s mac=%s ip=%s community_source=%s community=%s",
            item.operation_id,
            item.sg_id,
            item.mac_address,
            ip_address,
            community_source,
            write_community,
        )
        precheck_status, precheck_message = self._precheck_executor(cm)
        precheck_result = OperationStageResultModel(
            stage=OperationStage.PRECHECK,
            status_code=precheck_status,
            transaction_ids=[],
            filenames=[],
            message=precheck_message,
            started_epoch=now_epoch,
            finished_epoch=now_epoch,
        )
        stages.append(precheck_result)
        if precheck_status != ServiceStatusCode.SUCCESS:
            self.logger.info(
                "rxmer worker precheck_failed operation_id=%s sg_id=%s mac=%s status=%s message=%s",
                item.operation_id,
                item.sg_id,
                item.mac_address,
                precheck_status.value,
                precheck_message,
            )
            return OperationWorkerResultModel(ip_address=ip_address, stages=stages)

        capture_result = self._run_capture(
            operation_id=item.operation_id,
            sg_id=item.sg_id,
            mac_address=item.mac_address,
            cable_modem=cm,
            channel_ids=list(request_summary.channel_ids),
            request_context=request_context,
        )
        stages.append(capture_result)
        self.logger.info(
            "rxmer worker complete operation_id=%s sg_id=%s mac=%s status=%s message=%s tx_count=%s file_count=%s",
            item.operation_id,
            item.sg_id,
            item.mac_address,
            capture_result.status_code.value,
            capture_result.message,
            len(capture_result.transaction_ids),
            len(capture_result.filenames),
        )
        return OperationWorkerResultModel(ip_address=ip_address, stages=stages)

    def _resolve_modem_ip(
        self,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
    ) -> InetAddressStr | None:
        store = self._sgw_store if self._sgw_store is not None else get_sgw_store()
        if store is None:
            self.logger.info(
                "rxmer modem ip unresolved sg_id=%s mac=%s reason=sgw_store_missing",
                sg_id,
                mac_address,
            )
            return None
        if self._sgw_store is None:
            self._sgw_store = store
        entry = store.get_entry(sg_id)
        if entry is None:
            self.logger.info(
                "rxmer modem ip unresolved sg_id=%s mac=%s reason=sg_entry_missing",
                sg_id,
                mac_address,
            )
            return None
        matched_modem = False
        for modem in entry.snapshot.cable_modems:
            if modem.mac != mac_address:
                continue
            matched_modem = True
            raw_ipv4 = str(modem.ipv4).strip()
            raw_ipv6 = str(modem.ipv6).strip()
            normalized_ipv4 = self._normalize_ip_value(raw_ipv4)
            normalized_ipv6 = self._normalize_ip_value(raw_ipv6)
            ip_value = self._select_ip(modem)
            self.logger.info(
                "rxmer modem ip candidates sg_id=%s mac=%s ipv4_raw=%s ipv4_norm=%s ipv6_raw=%s ipv6_norm=%s",
                sg_id,
                mac_address,
                raw_ipv4,
                normalized_ipv4,
                raw_ipv6,
                normalized_ipv6,
            )
            if ip_value is None:
                self.logger.info(
                    "rxmer modem ip unresolved sg_id=%s mac=%s",
                    sg_id,
                    mac_address,
                )
                return None
            try:
                return InetAddressStr(str(Inet(ip_value)))
            except Exception:
                self.logger.info(
                    "rxmer modem ip invalid sg_id=%s mac=%s ip_selected=%s",
                    sg_id,
                    mac_address,
                    ip_value,
                )
                return None
        if not matched_modem:
            self.logger.info(
                "rxmer modem ip unresolved sg_id=%s mac=%s reason=modem_not_in_sg_snapshot",
                sg_id,
                mac_address,
            )
        return None

    @staticmethod
    def _select_ip(modem: SgwCableModemModel) -> str | None:
        ipv4 = RxMerCaptureWorker._normalize_ip_value(str(modem.ipv4))
        if ipv4 not in {"", "0.0.0.0"}:
            return ipv4
        ipv6 = RxMerCaptureWorker._normalize_ip_value(str(modem.ipv6))
        if ipv6 not in {"", "::"}:
            return ipv6
        return None

    @staticmethod
    def _normalize_ip_value(raw_value: str) -> str:
        value = raw_value.strip()
        if value == "":
            return ""
        if not value.startswith("0x"):
            return value
        return RxMerCaptureWorker._decode_hex_ip(value)

    @staticmethod
    def _decode_hex_ip(value: str) -> str:
        encoded = value[2:]
        if encoded == "":
            return ""
        try:
            if len(encoded) == 8:
                return str(ipaddress.IPv4Address(int(encoded, 16)))
            if len(encoded) == 32:
                return str(ipaddress.IPv6Address(int(encoded, 16)))
        except Exception:
            return value
        return value

    @staticmethod
    def _resolve_write_community(context: OperationRequestContextModel | None) -> str:
        if context is None or context.snmp_write_community is None:
            return PnmConfigManager.get_write_community()
        return str(context.snmp_write_community)

    def _run_capture(
        self,
        operation_id: PnmCaptureOperationId,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
        cable_modem: CableModem,
        channel_ids: list[ChannelId],
        request_context: OperationRequestContextModel | None,
    ) -> OperationStageResultModel:
        interface_parameters = None
        if channel_ids:
            interface_parameters = DownstreamOfdmParameters(channel_id=list(channel_ids))
        tftp_servers = self._resolve_tftp_servers(request_context)
        tftp_path = PnmConfigManager.get_tftp_path()
        self.logger.info(
            "RxMER-Worker [CAPTURE_START] operation_id=%s sg_id=%s mac=%s ip=%s channel_count=%s tftp_ipv4=%s tftp_ipv6=%s tftp_path=%s",
            operation_id,
            sg_id,
            mac_address,
            cable_modem.get_inet_address,
            len(channel_ids),
            str(tftp_servers[0]),
            str(tftp_servers[1]),
            tftp_path,
        )
        capture_response = self._capture_executor(cable_modem, interface_parameters, tftp_servers, tftp_path)
        status_code, transaction_id, filename, message = self._parse_capture_response(capture_response)
        created_epoch = self._now_epoch()
        final_transaction_ids: list[TransactionId] = []
        final_filenames: list[FileNameStr] = []
        final_message = message
        if status_code == ServiceStatusCode.SUCCESS and filename is not None and transaction_id is not None:
            final_transaction_ids = [transaction_id]
            final_filenames = [filename]
        else:
            final_message = message or MISSING_TRANSACTION_MESSAGE
        self.logger.info(
            "RxMER-Worker [CAPTURE_RESULT] operation_id=%s sg_id=%s mac=%s status=%s message=%s tx_id=%s filename=%s",
            operation_id,
            sg_id,
            mac_address,
            status_code.value,
            final_message,
            transaction_id if transaction_id is not None else "",
            filename if filename is not None else "",
        )
        return OperationStageResultModel(
            stage=OperationStage.CAPTURE,
            status_code=status_code,
            transaction_ids=final_transaction_ids,
            filenames=final_filenames,
            message=final_message,
            started_epoch=created_epoch,
            finished_epoch=created_epoch,
        )

    @staticmethod
    def _resolve_tftp_servers(context: OperationRequestContextModel | None) -> tuple[Inet, Inet]:
        default_v4, default_v6 = PnmConfigManager.get_tftp_servers()
        ipv4 = default_v4 if context is None or context.tftp_ipv4 is None else Inet(str(context.tftp_ipv4))
        ipv6 = default_v6 if context is None or context.tftp_ipv6 is None else Inet(str(context.tftp_ipv6))
        return (ipv4, ipv6)

    @staticmethod
    def _parse_capture_response(
        response: MessageResponse | None,
    ) -> tuple[ServiceStatusCode, TransactionId | None, FileNameStr | None, str]:
        if response is None:
            return (ServiceStatusCode.FAILURE, None, None, NO_MESSAGE_RESPONSE)
        status_code = response.status
        if status_code != ServiceStatusCode.SUCCESS:
            return (status_code, None, None, f"{status_code.name}")
        payload = response.payload
        if not isinstance(payload, list):
            return (ServiceStatusCode.FAILURE, None, None, MISSING_TRANSACTION_MESSAGE)
        for element in payload:
            message_type, message = RxMerCaptureWorker._extract_payload_entry(element)
            if message_type != MessageResponseType.PNM_FILE_TRANSACTION.name:
                continue
            if not isinstance(message, dict):
                continue
            transaction_id = message.get("transaction_id")
            filename = message.get("filename")
            if transaction_id is None or filename is None:
                continue
            return (
                status_code,
                TransactionId(str(transaction_id)),
                FileNameStr(str(filename)),
                CLEAR_MESSAGE,
            )
        return (ServiceStatusCode.PNM_FILE_TRANSACTION_ID_NOT_FOUND, None, None, MISSING_TRANSACTION_MESSAGE)

    @staticmethod
    def _extract_payload_entry(
        element: MessagePayload | dict[str, object],
    ) -> tuple[str | None, object | None]:
        if isinstance(element, MessagePayload):
            return (element.message_type, element.message)
        if isinstance(element, dict):
            message_type = element.get("message_type")
            message = element.get("message")
            return (
                str(message_type) if message_type is not None else None,
                message,
            )
        return (None, None)

    @staticmethod
    def _now_epoch() -> TimestampSec:
        return TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))


def _run_pypnm_capture(
    cable_modem: CableModem,
    interface_parameters: DownstreamOfdmParameters | None,
    tftp_servers: tuple[Inet, Inet],
    tftp_path: str,
) -> MessageResponse:
    service = CmDsOfdmRxMerService(cable_modem, tftp_servers, tftp_path)
    loop = asyncio.DefaultEventLoopPolicy().new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(service.set_and_go(interface_parameters=interface_parameters))
    finally:
        with suppress(Exception):
            loop.run_until_complete(loop.shutdown_asyncgens())
        asyncio.set_event_loop(None)
        loop.close()


class RxMerServiceGroupOperationService:
    """Service layer for SG-level RxMER operation lifecycle endpoints."""

    def __init__(
        self,
        store: OperationStore | None = None,
        runner: OperationRunner | None = None,
        capture_executor: CaptureExecutor | None = None,
        precheck_executor: PrecheckExecutor | None = None,
        sgw_store: SgwCacheStore | None = None,
        max_inline_records: int = DEFAULT_MAX_INLINE_RECORDS,
    ) -> None:
        self._store = store or OperationStore()
        self._capture_executor = capture_executor or _run_pypnm_capture
        self._precheck_executor = precheck_executor or self._run_precheck
        self._sgw_store = sgw_store or get_sgw_store()
        if runner is None:
            worker = RxMerCaptureWorker(
                store=self._store,
                capture_executor=self._capture_executor,
                precheck_executor=self._precheck_executor,
                sgw_store=self._sgw_store,
            )
            runner = OperationRunner(self._store, worker=worker)
        self._runner = runner
        self._max_inline_records = max_inline_records
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def start_capture(
        self,
        request: RxMerServiceGroupStartCaptureRequest,
    ) -> RxMerServiceGroupStartCaptureResponse:
        """Create a new SG-level RxMER operation state record."""
        request_summary = self._build_request_summary(request)
        request_context = self._build_request_context(request)
        state = self._store.create_operation(request_summary, request_context)
        self.logger.info(
            "RxMer-StartCapture [QUEUED] operation_id=%s, scope_sg=%s, scope_macs=%s",
            state.operation_id,
            len(state.request_summary.serving_group_ids),
            len(state.request_summary.mac_addresses),
        )
        started = self._runner.start(state.operation_id)
        if not started:
            self.logger.warning("Operation-Runner already active for %s", state.operation_id)
        return RxMerServiceGroupStartCaptureResponse(
            status=ServiceStatusCode.SUCCESS,
            message="",
            operation=state,
        )

    def status(
        self,
        request: RxMerServiceGroupOperationRequest,
    ) -> RxMerServiceGroupStatusResponse:
        """Return the persisted state for an operation."""
        try:
            state = self._store.load_state(request.pnm_capture_operation_id)
        except FileNotFoundError:
            return RxMerServiceGroupStatusResponse(
                status=ServiceStatusCode.FAILURE,
                message=NOT_FOUND_MESSAGE,
                operation=None,
            )
        message = ""
        if state.state == OperationState.COMPLETED and state.counters.total_modems == 0:
            message = "no modems selected"
        return RxMerServiceGroupStatusResponse(
            status=ServiceStatusCode.SUCCESS,
            message=message,
            operation=state,
        )

    def cancel(
        self,
        request: RxMerServiceGroupOperationRequest,
    ) -> RxMerServiceGroupCancelResponse:
        """Request cancellation for an operation."""
        try:
            state = self._runner.request_cancel(request.pnm_capture_operation_id)
        except FileNotFoundError:
            return RxMerServiceGroupCancelResponse(
                status=ServiceStatusCode.FAILURE,
                message=NOT_FOUND_MESSAGE,
                operation=None,
            )
        return RxMerServiceGroupCancelResponse(
            status=ServiceStatusCode.SUCCESS,
            message="",
            operation=state,
        )

    def results(
        self,
        request: RxMerServiceGroupOperationRequest,
    ) -> RxMerServiceGroupResultsResponse:
        """Return linkage records for an operation when available."""
        try:
            self._store.load_state(request.pnm_capture_operation_id)
        except FileNotFoundError:
            return RxMerServiceGroupResultsResponse(
                status=ServiceStatusCode.FAILURE,
                message=NOT_FOUND_MESSAGE,
            )

        files_scanned = self._store.count_result_files(request.pnm_capture_operation_id)
        total_records = self._store.count_result_records(request.pnm_capture_operation_id)
        include_records = total_records <= self._max_inline_records
        records = []
        if include_records:
            records = self._store.load_result_records(request.pnm_capture_operation_id)
        summary = OperationResultsSummaryModel(
            record_count=total_records,
            included_count=len(records),
            files_scanned=files_scanned,
        )
        message = "" if total_records > 0 else "no results recorded"
        return RxMerServiceGroupResultsResponse(
            status=ServiceStatusCode.SUCCESS,
            message=message,
            summary=summary,
            records=records,
        )

    @staticmethod
    def _build_request_context(
        request: RxMerServiceGroupStartCaptureRequest,
    ) -> OperationRequestContextModel:
        cmts = request.cmts
        pnm = cmts.cable_modem.pnm_parameters
        tftp = pnm.tftp if pnm is not None else None
        snmp = cmts.cable_modem.snmp
        snmp_v2c = snmp.snmpV2C if snmp is not None else None
        return OperationRequestContextModel(
            tftp_ipv4=tftp.ipv4 if tftp is not None else None,
            tftp_ipv6=tftp.ipv6 if tftp is not None else None,
            snmp_write_community=snmp_v2c.community if snmp_v2c is not None else None,
        )

    @staticmethod
    def _run_precheck(cable_modem: CableModem) -> tuple[ServiceStatusCode, str]:
        try:
            return asyncio.run(
                CableModemServicePreCheck(cable_modem=cable_modem, validate_ofdm_exist=True).run_precheck()
            )
        except Exception as exc:
            return (ServiceStatusCode.FAILURE, f"{PRECHECK_FAILURE_MESSAGE}: {exc}")

    def _build_request_summary(
        self,
        request: RxMerServiceGroupStartCaptureRequest,
    ) -> OperationRequestSummaryModel:
        cmts = request.cmts
        channel_ids = RxMerServiceGroupOperationService._resolve_channel_ids(cmts)
        requested_sg_ids = list(cmts.serving_group.id)
        requested_mac_addresses = list(cmts.cable_modem.mac_address)
        serving_group_ids, mac_addresses = self._resolve_modem_scope(requested_sg_ids, requested_mac_addresses)
        self.logger.info(
            "rxmer request scope requested_sg=%s requested_macs=%s resolved_sg=%s resolved_macs=%s channel_count=%s",
            len(requested_sg_ids),
            len(requested_mac_addresses),
            len(serving_group_ids),
            len(mac_addresses),
            len(channel_ids),
        )
        execution = request.execution
        return OperationRequestSummaryModel(
            serving_group_ids=serving_group_ids,
            mac_addresses=mac_addresses,
            channel_ids=channel_ids,
            execution=OperationExecutionModel(
                max_workers=execution.max_workers,
                retry_count=execution.retry_count,
                retry_delay_seconds=execution.retry_delay_seconds,
                per_modem_timeout_seconds=execution.per_modem_timeout_seconds,
                overall_timeout_seconds=execution.overall_timeout_seconds,
            ),
        )

    def _resolve_modem_scope(
        self,
        requested_sg_ids: list[ServiceGroupId],
        requested_mac_addresses: list[MacAddressStr],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        if requested_sg_ids and requested_mac_addresses:
            return requested_sg_ids, requested_mac_addresses
        store = self._sgw_store if self._sgw_store is not None else get_sgw_store()
        if store is None:
            return requested_sg_ids, requested_mac_addresses
        if self._sgw_store is None:
            self._sgw_store = store

        sg_ids = requested_sg_ids if requested_sg_ids else store.get_ids()
        if not sg_ids:
            return ([], [])

        cache_entries = self._load_cache_entries(sg_ids)
        if requested_mac_addresses:
            return self._expand_macs_with_wildcard_sg(requested_mac_addresses, cache_entries)
        return self._expand_modems_for_sgs(cache_entries)

    def _load_cache_entries(
        self,
        sg_ids: list[ServiceGroupId],
    ) -> list[tuple[ServiceGroupId, list[SgwCableModemModel]]]:
        entries: list[tuple[ServiceGroupId, list[SgwCableModemModel]]] = []
        store = self._sgw_store
        if store is None:
            return entries
        for sg_id in sg_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                continue
            entries.append((sg_id, list(entry.snapshot.cable_modems)))
        return entries

    @staticmethod
    def _expand_macs_with_wildcard_sg(
        requested_mac_addresses: list[MacAddressStr],
        cache_entries: list[tuple[ServiceGroupId, list[SgwCableModemModel]]],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        mac_to_sg_ids: dict[MacAddressStr, list[ServiceGroupId]] = {}
        for sg_id, cable_modems in cache_entries:
            for cable_modem in cable_modems:
                if cable_modem.mac not in mac_to_sg_ids:
                    mac_to_sg_ids[cable_modem.mac] = []
                mac_to_sg_ids[cable_modem.mac].append(sg_id)

        expanded_sg_ids: list[ServiceGroupId] = []
        expanded_mac_addresses: list[MacAddressStr] = []
        for mac_address in requested_mac_addresses:
            sg_ids = mac_to_sg_ids.get(mac_address)
            if sg_ids is None:
                continue
            for sg_id in sg_ids:
                expanded_sg_ids.append(sg_id)
                expanded_mac_addresses.append(mac_address)
        return (expanded_sg_ids, expanded_mac_addresses)

    @staticmethod
    def _expand_modems_for_sgs(
        cache_entries: list[tuple[ServiceGroupId, list[SgwCableModemModel]]],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        expanded_sg_ids: list[ServiceGroupId] = []
        expanded_mac_addresses: list[MacAddressStr] = []
        for sg_id, cable_modems in cache_entries:
            for cable_modem in cable_modems:
                expanded_sg_ids.append(sg_id)
                expanded_mac_addresses.append(cable_modem.mac)
        return (expanded_sg_ids, expanded_mac_addresses)

    @staticmethod
    def _resolve_channel_ids(cmts: CmtsRequestEnvelopeModel) -> list[ChannelId]:
        pnm = cmts.cable_modem.pnm_parameters
        capture = pnm.capture if pnm is not None else None
        channel_ids = capture.channel_ids if capture is not None else None
        if not channel_ids:
            return []
        return list(channel_ids)


__all__ = [
    "RxMerServiceGroupOperationService",
]

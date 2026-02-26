# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from collections.abc import Callable

from pypnm.api.routes.common.classes.common_endpoint_classes.common.enum import (
    AnalysisType,
)
from pypnm.api.routes.common.classes.operation.cable_modem_precheck import (
    CableModemServicePreCheck,
)
from pypnm.api.routes.common.extended.common_messaging_service import (
    MessageResponse,
    MessageResponseType,
)
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.api.routes.docs.pnm.ds.histogram.service import CmDsHistogramService
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.docsis.cable_modem import CableModem
from pypnm.lib.inet import Inet
from pypnm.lib.types import (
    FileNameStr,
    InetAddressStr,
    MacAddressStr,
    TimestampSec,
    TransactionId,
)

from pypnm_cmts.api.common.operations.logging import short_op_id
from pypnm_cmts.api.common.operations.models import (
    OperationExecutionModel,
    OperationRequestContextModel,
    OperationRequestSummaryModel,
    OperationResultsSummaryModel,
    OperationStageResultModel,
    OperationStateModel,
    PerModemLinkageRecordModel,
)
from pypnm_cmts.api.common.operations.runner import (
    OperationRunner,
    OperationWorkItemModel,
)
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.common.service.pnm.asyncio_runner import PnmAsyncioRunner
from pypnm_cmts.api.common.service.pnm.capture import PnmCaptureHelper
from pypnm_cmts.api.common.service.pnm.capture_worker import (
    PnmCaptureWorkerBase,
    PrecheckExecutor,
)
from pypnm_cmts.api.common.service.pnm.constants import (
    MISSING_TRANSACTION_MESSAGE,
    NO_MESSAGE_RESPONSE,
    PRECHECK_FAILURE_MESSAGE,
)
from pypnm_cmts.api.common.service.pnm.logging import (
    build_request_scope_log,
    build_start_capture_queued_log,
)
from pypnm_cmts.api.common.service.pnm.modem import PnmModemResolver
from pypnm_cmts.api.common.service.pnm.operation_service import (
    DEFAULT_MAX_INLINE_RECORDS,
    PnmServiceGroupOperationServiceBase,
)
from pypnm_cmts.api.common.service.pnm.results_analysis import (
    PnmStoredCaptureAnalysisResultModel,
    PnmStoredCaptureAnalysisService,
)
from pypnm_cmts.api.common.service.pnm.results_schemas import (
    PnmAnalyzedFileLinkModel,
    PnmResultsStageMessagesModel,
    PnmResultsStageStatusCodesModel,
)
from pypnm_cmts.api.routes.pnm.sg.ds.histogram.schemas import (
    DsHistogramResultsCableModemModel,
    DsHistogramResultsDataModel,
    DsHistogramResultsServingGroupModel,
    DsHistogramServiceGroupCancelResponse,
    DsHistogramServiceGroupOperationRequest,
    DsHistogramServiceGroupResultsModel,
    DsHistogramServiceGroupResultsRequest,
    DsHistogramServiceGroupResultsResponse,
    DsHistogramServiceGroupStartCaptureRequest,
    DsHistogramServiceGroupStartCaptureResponse,
    DsHistogramServiceGroupStatusResponse,
)
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings
from pypnm_cmts.lib.constants import OperationStage, PnmCaptureStatus
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId
from pypnm_cmts.sgw.runtime_state import get_sgw_store
from pypnm_cmts.sgw.store import SgwCacheStore

CaptureExecutor = Callable[
    [CableModem, tuple[Inet, Inet], str, OperationRequestContextModel | None],
    MessageResponse,
]


class DsHistogramCaptureWorker(PnmCaptureWorkerBase):
    """Execute eligibility, precheck, and capture stages for a single modem."""

    def __init__(
        self,
        store: OperationStore,
        capture_executor: CaptureExecutor,
        precheck_executor: PrecheckExecutor,
        sgw_store: SgwCacheStore | None,
    ) -> None:
        super().__init__(store=store, precheck_executor=precheck_executor)
        self._capture_executor = capture_executor
        self._sgw_store = sgw_store

    @property
    def _worker_log_prefix(self) -> str:
        return "DsHistogram"

    def _run_capture_stage(
        self,
        item: OperationWorkItemModel,
        request_summary: OperationRequestSummaryModel,
        request_context: OperationRequestContextModel | None,
        cable_modem: CableModem,
    ) -> OperationStageResultModel:
        return self._run_capture(
            operation_id=item.operation_id,
            sg_id=item.sg_id,
            mac_address=item.mac_address,
            cable_modem=cable_modem,
            request_context=request_context,
        )

    def _resolve_modem_ip(
        self,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
    ) -> InetAddressStr | None:
        active_store = self._sgw_store if self._sgw_store is not None else get_sgw_store()
        resolved_ip, store = PnmModemResolver.resolve_modem_ip(
            sgw_store=active_store,
            sg_id=sg_id,
            mac_address=mac_address,
            logger=self.logger,
            log_prefix="",
        )
        if self._sgw_store is None and store is not None:
            self._sgw_store = store
        return resolved_ip

    def _run_capture(
        self,
        operation_id: PnmCaptureOperationId,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
        cable_modem: CableModem,
        request_context: OperationRequestContextModel | None,
    ) -> OperationStageResultModel:
        tftp_servers = PnmCaptureHelper.resolve_tftp_servers(request_context)
        tftp_path = PnmConfigManager.get_tftp_path()
        modem_ip = str(cable_modem.get_inet_address)
        tftp_log_key, tftp_log_value = PnmCaptureHelper.resolve_tftp_log_target(modem_ip=modem_ip, tftp_servers=tftp_servers)
        self.logger.info(
            "[CAPTURE_START] operation_id=%s sg_id=%s mac=%s ip=%s %s=%s tftp_path=\"%s\"",
            short_op_id(operation_id),
            sg_id,
            mac_address,
            modem_ip,
            tftp_log_key,
            tftp_log_value,
            tftp_path,
        )
        capture_response = self._capture_executor(cable_modem, tftp_servers, tftp_path, request_context)
        status_code, transaction_id, filename, message = PnmCaptureHelper.parse_capture_response(
            response=capture_response,
            expected_message_type=MessageResponseType.PNM_FILE_TRANSACTION.name,
            no_message_response=NO_MESSAGE_RESPONSE,
            missing_transaction_message=MISSING_TRANSACTION_MESSAGE,
        )
        created_epoch = PnmCaptureHelper.now_epoch()
        final_transaction_ids: list[TransactionId] = []
        final_filenames: list[FileNameStr] = []
        final_message = message
        if status_code == ServiceStatusCode.SUCCESS and filename is not None and transaction_id is not None:
            final_transaction_ids = [transaction_id]
            final_filenames = [filename]
        else:
            final_message = message or MISSING_TRANSACTION_MESSAGE
        self.logger.info(
            "[CAPTURE_RESULT] operation_id=%s sg_id=%s mac=%s status=%s message=\"%s\" tx_id=%s filename=%s",
            short_op_id(operation_id),
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


class DsHistogramCaptureExecutor:
    """Downstream Histogram-specific capture executor helpers."""

    @staticmethod
    def run_pypnm_capture(
        cable_modem: CableModem,
        tftp_servers: tuple[Inet, Inet],
        tftp_path: str,
        request_context: OperationRequestContextModel | None,
    ) -> MessageResponse:
        sample_duration = 10
        if request_context is not None and request_context.histogram_sample_duration is not None:
            sample_duration = int(request_context.histogram_sample_duration)

        service = CmDsHistogramService(
            cable_modem=cable_modem,
            sample_duration=sample_duration,
            tftp_servers=tftp_servers,
            tftp_path=tftp_path,
        )
        return PnmAsyncioRunner.run_on_isolated_event_loop(service.set_and_go())


class DsHistogramServiceGroupOperationService(PnmServiceGroupOperationServiceBase):
    """Service layer for SG-level downstream Histogram operation lifecycle endpoints."""

    def __init__(
        self,
        store: OperationStore | None = None,
        runner: OperationRunner | None = None,
        capture_executor: CaptureExecutor | None = None,
        precheck_executor: PrecheckExecutor | None = None,
        sgw_store: SgwCacheStore | None = None,
        max_inline_records: int = DEFAULT_MAX_INLINE_RECORDS,
        results_analysis_service: PnmStoredCaptureAnalysisService | None = None,
    ) -> None:
        super().__init__(
            store=store,
            sgw_store=sgw_store,
            runtime_store_loader=lambda: get_sgw_store(),
            max_inline_records=max_inline_records,
        )
        self._capture_executor = capture_executor or DsHistogramCaptureExecutor.run_pypnm_capture
        self._precheck_executor = precheck_executor or self._run_precheck
        if runner is None:
            worker = DsHistogramCaptureWorker(
                store=self._store,
                capture_executor=self._capture_executor,
                precheck_executor=self._precheck_executor,
                sgw_store=self._sgw_store,
            )
            runner = OperationRunner(self._store, worker=worker)
        self._runner = runner
        self._results_analysis_service = results_analysis_service or PnmStoredCaptureAnalysisService()

    def results(
        self,
        request: DsHistogramServiceGroupOperationRequest | DsHistogramServiceGroupResultsRequest,
    ) -> DsHistogramServiceGroupResultsResponse:
        """Return operation results and decode basic histogram analysis when available."""
        operation_id = self._extract_operation_id(request)
        status, message, summary, records = self._load_operation_results(operation_id)
        request_context = self._store.load_request_context(operation_id)
        results_request = request if isinstance(request, DsHistogramServiceGroupResultsRequest) else None
        filtered_records = records if results_request is None else self._filter_results_records(records, results_request)
        return DsHistogramServiceGroupResultsResponse(
            status=status,
            message=message,
            results=self._build_structured_results(
                filtered_records,
                results_request,
                cmts_hostname=self._resolve_results_cmts_hostname(request_context),
            ),
            summary=summary,
            records=filtered_records,
        )

    def _log_start_capture(self, state: OperationStateModel) -> None:
        self.logger.info(
            build_start_capture_queued_log(
                operation_name="DsHistogram",
                operation_id=state.operation_id,
                scope_sg_count=len(state.request_summary.serving_group_ids),
                scope_mac_count=len(state.request_summary.mac_addresses),
            )
        )

    @staticmethod
    def _build_request_context(
        request: DsHistogramServiceGroupStartCaptureRequest,
    ) -> OperationRequestContextModel:
        cmts = request.cmts
        pnm = cmts.cable_modem.pnm_parameters
        tftp = pnm.tftp if pnm is not None else None
        snmp = cmts.cable_modem.snmp
        snmp_v2c = snmp.snmpV2C if snmp is not None else None
        return OperationRequestContextModel(
            cmts_hostname=DsHistogramServiceGroupOperationService._resolve_capture_cmts_hostname(),
            tftp_ipv4=tftp.ipv4 if tftp is not None else None,
            tftp_ipv6=tftp.ipv6 if tftp is not None else None,
            snmp_write_community=snmp_v2c.community if snmp_v2c is not None else None,
            histogram_sample_duration=request.capture_settings.sample_duration,
        )

    @staticmethod
    def _run_precheck(cable_modem: CableModem) -> tuple[ServiceStatusCode, str]:
        try:
            return PnmAsyncioRunner.run_on_isolated_event_loop(
                CableModemServicePreCheck(cable_modem=cable_modem).run_precheck()
            )
        except Exception as exc:
            return (ServiceStatusCode.FAILURE, f"{PRECHECK_FAILURE_MESSAGE}: {exc}")

    @staticmethod
    def _extract_operation_id(
        request: DsHistogramServiceGroupOperationRequest | DsHistogramServiceGroupResultsRequest,
    ) -> PnmCaptureOperationId:
        operation_id = getattr(request, "pnm_capture_operation_id", None)
        if operation_id is not None:
            return operation_id
        return request.operation.pnm_capture_operation_id

    @staticmethod
    def _build_start_response(
        state: OperationStateModel,
    ) -> DsHistogramServiceGroupStartCaptureResponse:
        return DsHistogramServiceGroupStartCaptureResponse(
            status=ServiceStatusCode.SUCCESS,
            message="",
            operation=state,
        )

    @staticmethod
    def _build_status_response(
        status: ServiceStatusCode,
        message: str,
        state: OperationStateModel | None,
    ) -> DsHistogramServiceGroupStatusResponse:
        return DsHistogramServiceGroupStatusResponse(
            status=status,
            message=message,
            operation=state,
        )

    @staticmethod
    def _build_cancel_response(
        status: ServiceStatusCode,
        message: str,
        state: OperationStateModel | None,
    ) -> DsHistogramServiceGroupCancelResponse:
        return DsHistogramServiceGroupCancelResponse(
            status=status,
            message=message,
            operation=state,
        )

    @staticmethod
    def _build_results_response(
        status: ServiceStatusCode,
        message: str,
        summary: OperationResultsSummaryModel,
        records: list[PerModemLinkageRecordModel],
    ) -> DsHistogramServiceGroupResultsResponse:
        return DsHistogramServiceGroupResultsResponse(
            status=status,
            message=message,
            summary=summary,
            records=records,
        )

    def _build_structured_results(
        self,
        records: list[PerModemLinkageRecordModel],
        request: DsHistogramServiceGroupResultsRequest | None = None,
        cmts_hostname: str | None = None,
    ) -> DsHistogramServiceGroupResultsModel:
        capture_finished_epochs = [
            int(record.finished_epoch)
            for record in records
            if record.stage == OperationStage.CAPTURE and int(record.finished_epoch) > 0
        ]
        modem_records: dict[str, list[PerModemLinkageRecordModel]] = {}
        for record in records:
            mac = str(record.mac_address)
            modem_records.setdefault(mac, []).append(record)

        decoded_by_txn = self._decode_records_basic_analysis(request, records)
        serving_groups_by_key: dict[int | None, DsHistogramResultsServingGroupModel] = {}
        for mac in sorted(modem_records.keys()):
            modem_stage_records = modem_records[mac]
            capture_records = [r for r in modem_stage_records if r.stage == OperationStage.CAPTURE]
            source_records = capture_records if capture_records else modem_stage_records
            transaction_ids: list[TransactionId] = []
            filenames: list[FileNameStr] = []
            for source in source_records:
                for transaction_id in source.transaction_ids:
                    if transaction_id not in transaction_ids:
                        transaction_ids.append(transaction_id)
                for filename in source.filenames:
                    if filename not in filenames:
                        filenames.append(filename)

            stage_status_codes = PnmResultsStageStatusCodesModel()
            stage_messages = PnmResultsStageMessagesModel()
            has_stage_messages = False
            for source in modem_stage_records:
                DsHistogramServiceGroupOperationService._set_stage_status_code(stage_status_codes, source)
                if source.message != "":
                    DsHistogramServiceGroupOperationService._set_stage_message(stage_messages, source)
                    has_stage_messages = True

            final_stage_record = DsHistogramServiceGroupOperationService._select_final_stage_record(modem_stage_records)
            modem_status = PnmCaptureStatus.SUCCESS
            modem_message = ""
            if final_stage_record is None or final_stage_record.status_code != ServiceStatusCode.SUCCESS:
                modem_status = PnmCaptureStatus.FAILED
                modem_message = "" if final_stage_record is None else final_stage_record.message
            elif final_stage_record.message != "":
                modem_message = final_stage_record.message

            modem_sg_id = ServiceGroupId(int(modem_stage_records[0].sg_id)) if modem_stage_records else None
            analysis_payload, pnm_file_type, analysis_error, analyzed_transaction_id = self._resolve_modem_analysis(
                request=request,
                modem_status=modem_status,
                transaction_ids=transaction_ids,
                decoded_by_txn=decoded_by_txn,
            )
            system_description = self._resolve_modem_system_description(
                transaction_ids=transaction_ids,
                decoded_by_txn=decoded_by_txn,
                analyzed_transaction_id=analyzed_transaction_id,
            )

            modem_model = DsHistogramResultsCableModemModel(
                mac_address=mac,
                system_description=system_description,
                status=modem_status,
                message=modem_message,
                histogram_data=DsHistogramResultsDataModel(
                    file=self._build_modem_file_link(
                        transaction_ids=transaction_ids,
                        filenames=filenames,
                        analyzed_transaction_id=analyzed_transaction_id,
                    ),
                    stage_status_codes=stage_status_codes,
                    stage_messages=stage_messages if has_stage_messages else None,
                    pnm_file_type=pnm_file_type,
                    analysis=analysis_payload,
                    analysis_error=analysis_error,
                ),
            )

            sg_key = int(modem_sg_id) if modem_sg_id is not None else None
            sg_group = serving_groups_by_key.get(sg_key)
            if sg_group is None:
                sg_group = DsHistogramResultsServingGroupModel(service_group_id=modem_sg_id, cable_modems=[])
                serving_groups_by_key[sg_key] = sg_group
            sg_group.cable_modems.append(modem_model)

        serving_groups = [
            serving_groups_by_key[key]
            for key in sorted(serving_groups_by_key.keys(), key=lambda item: -1 if item is None else item)
        ]
        results = DsHistogramServiceGroupResultsModel()
        results.capture_details.capture_time_epoch = (
            TimestampSec(max(capture_finished_epochs)) if capture_finished_epochs else None
        )
        results.cmts.cmts_hostname = cmts_hostname
        results.channels = []
        results.serving_groups = serving_groups
        return results

    def _filter_results_records(
        self,
        records: list[PerModemLinkageRecordModel],
        request: DsHistogramServiceGroupResultsRequest,
    ) -> list[PerModemLinkageRecordModel]:
        selection = request.selection
        if not selection.serving_group_ids and not selection.mac_addresses:
            return records
        allowed_sg_ids = {int(sg_id) for sg_id in selection.serving_group_ids}
        allowed_macs = {str(mac).lower() for mac in selection.mac_addresses}
        filtered: list[PerModemLinkageRecordModel] = []
        for record in records:
            if allowed_sg_ids and int(record.sg_id) not in allowed_sg_ids:
                continue
            if allowed_macs and str(record.mac_address).lower() not in allowed_macs:
                continue
            filtered.append(record)
        return filtered

    @staticmethod
    def _select_final_stage_record(
        modem_stage_records: list[PerModemLinkageRecordModel],
    ) -> PerModemLinkageRecordModel | None:
        stage_order = {OperationStage.ELIGIBILITY: 1, OperationStage.PRECHECK: 2, OperationStage.CAPTURE: 3}
        ordered = sorted(modem_stage_records, key=lambda record: stage_order.get(record.stage, 0))
        if not ordered:
            return None
        return ordered[-1]

    @staticmethod
    def _set_stage_status_code(
        stage_status_codes: PnmResultsStageStatusCodesModel,
        record: PerModemLinkageRecordModel,
    ) -> None:
        if record.stage == OperationStage.ELIGIBILITY:
            stage_status_codes.eligibility = record.status_code
            return
        if record.stage == OperationStage.PRECHECK:
            stage_status_codes.precheck = record.status_code
            return
        if record.stage == OperationStage.CAPTURE:
            stage_status_codes.capture = record.status_code

    @staticmethod
    def _set_stage_message(
        stage_messages: PnmResultsStageMessagesModel,
        record: PerModemLinkageRecordModel,
    ) -> None:
        if record.stage == OperationStage.ELIGIBILITY:
            stage_messages.eligibility = record.message
            return
        if record.stage == OperationStage.PRECHECK:
            stage_messages.precheck = record.message
            return
        if record.stage == OperationStage.CAPTURE:
            stage_messages.capture = record.message

    @staticmethod
    def _analysis_requested(
        request: DsHistogramServiceGroupResultsRequest | None,
    ) -> bool:
        return request is not None and request.analysis.type == AnalysisType.BASIC

    def _decode_records_basic_analysis(
        self,
        request: DsHistogramServiceGroupResultsRequest | None,
        records: list[PerModemLinkageRecordModel],
    ) -> dict[TransactionId, PnmStoredCaptureAnalysisResultModel]:
        if not DsHistogramServiceGroupOperationService._analysis_requested(request):
            return {}
        transaction_ids: list[TransactionId] = []
        for record in records:
            if record.stage != OperationStage.CAPTURE or record.status_code != ServiceStatusCode.SUCCESS:
                continue
            transaction_ids.extend(record.transaction_ids)
        if not transaction_ids:
            return {}
        return self._results_analysis_service.analyze_transactions_basic(transaction_ids)

    @staticmethod
    def _resolve_modem_analysis(
        request: DsHistogramServiceGroupResultsRequest | None,
        modem_status: PnmCaptureStatus,
        transaction_ids: list[TransactionId],
        decoded_by_txn: dict[TransactionId, PnmStoredCaptureAnalysisResultModel],
    ) -> tuple[dict[str, object] | None, str | None, str | None, TransactionId | None]:
        if not DsHistogramServiceGroupOperationService._analysis_requested(request):
            return (None, None, None, None)
        if modem_status != PnmCaptureStatus.SUCCESS or not transaction_ids:
            return (None, None, None, None)
        for transaction_id in transaction_ids:
            decoded = decoded_by_txn.get(transaction_id)
            if decoded is None:
                continue
            return (decoded.analysis, decoded.pnm_file_type, decoded.error, transaction_id)
        return (None, None, None, None)

    @staticmethod
    def _build_modem_file_link(
        transaction_ids: list[TransactionId],
        filenames: list[FileNameStr],
        analyzed_transaction_id: TransactionId | None,
    ) -> PnmAnalyzedFileLinkModel | None:
        if not transaction_ids and not filenames:
            return None
        selected_index = 0
        if analyzed_transaction_id is not None:
            for index, transaction_id in enumerate(transaction_ids):
                if transaction_id == analyzed_transaction_id:
                    selected_index = index
                    break
        transaction_id_value = str(transaction_ids[selected_index]) if selected_index < len(transaction_ids) else None
        filename_value = str(filenames[selected_index]) if selected_index < len(filenames) else None
        if transaction_id_value is None and filename_value is None:
            return None
        return PnmAnalyzedFileLinkModel(transaction_id=transaction_id_value, filename=filename_value)

    @staticmethod
    def _resolve_modem_system_description(
        transaction_ids: list[TransactionId],
        decoded_by_txn: dict[TransactionId, PnmStoredCaptureAnalysisResultModel],
        analyzed_transaction_id: TransactionId | None,
    ) -> dict[str, str] | None:
        selected_ids: list[TransactionId] = []
        if analyzed_transaction_id is not None:
            selected_ids.append(analyzed_transaction_id)
        selected_ids.extend([tx for tx in transaction_ids if tx != analyzed_transaction_id])
        for transaction_id in selected_ids:
            decoded = decoded_by_txn.get(transaction_id)
            if decoded is None or decoded.system_description is None:
                continue
            normalized: dict[str, str] = {}
            for key, value in decoded.system_description.items():
                normalized[str(key)] = str(value)
            return normalized or None
        return None

    @staticmethod
    def _resolve_results_cmts_hostname(
        request_context: OperationRequestContextModel | None,
    ) -> str | None:
        if request_context is not None and request_context.cmts_hostname is not None:
            hostname = str(request_context.cmts_hostname).strip()
            if hostname != "":
                return hostname
        return DsHistogramServiceGroupOperationService._resolve_capture_cmts_hostname()

    @staticmethod
    def _resolve_capture_cmts_hostname() -> str | None:
        try:
            hostname = str(CmtsSystemConfigSettings.cmts_device_hostname(0)).strip()
        except Exception:
            return None
        return hostname or None

    def _build_request_summary(
        self,
        request: DsHistogramServiceGroupStartCaptureRequest,
    ) -> OperationRequestSummaryModel:
        cmts = request.cmts
        requested_sg_ids = list(cmts.serving_group.id)
        requested_mac_addresses = list(cmts.cable_modem.mac_address)
        serving_group_ids, mac_addresses = self._resolve_modem_scope(requested_sg_ids, requested_mac_addresses)
        self.logger.info(
            build_request_scope_log(
                operation_name="DsHistogram",
                requested_sg_count=len(requested_sg_ids),
                requested_mac_count=len(requested_mac_addresses),
                resolved_sg_count=len(serving_group_ids),
                resolved_mac_count=len(mac_addresses),
            )
        )
        execution = request.execution
        return OperationRequestSummaryModel(
            serving_group_ids=serving_group_ids,
            mac_addresses=mac_addresses,
            channel_ids=[],
            execution=OperationExecutionModel(
                max_workers=execution.max_workers,
                retry_count=execution.retry_count,
                retry_delay_seconds=execution.retry_delay_seconds,
                per_modem_timeout_seconds=execution.per_modem_timeout_seconds,
                overall_timeout_seconds=execution.overall_timeout_seconds,
            ),
        )


__all__ = [
    "DsHistogramServiceGroupOperationService",
]

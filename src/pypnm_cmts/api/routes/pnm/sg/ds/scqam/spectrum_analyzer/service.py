# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from collections.abc import Callable

from pypnm.api.routes.common.classes.operation.cable_modem_precheck import (
    CableModemServicePreCheck,
)
from pypnm.api.routes.common.extended.common_messaging_service import (
    MessageResponse,
    MessageResponseType,
)
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.api.routes.docs.pnm.spectrumAnalyzer.service import (
    DsScQamChannelSpectrumAnalyzer,
)
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.docsis.cable_modem import CableModem
from pypnm.docsis.cm_snmp_operation import SpectrumRetrievalType
from pypnm.lib.inet import Inet
from pypnm.lib.types import (
    ChannelId,
    FileNameStr,
    InetAddressStr,
    MacAddressStr,
    ResolutionBw,
    TransactionId,
)

from pypnm_cmts.api.common.cmts_request import CmtsRequestEnvelopeModel
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
    CLEAR_MESSAGE,
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
from pypnm_cmts.api.routes.pnm.sg.ds.scqam.spectrum_analyzer.schemas import (
    ScQamSpectrumAnalyzerServiceGroupCancelResponse,
    ScQamSpectrumAnalyzerServiceGroupOperationRequest,
    ScQamSpectrumAnalyzerServiceGroupResultsResponse,
    ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest,
    ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse,
    ScQamSpectrumAnalyzerServiceGroupStatusResponse,
)
from pypnm_cmts.lib.constants import OperationStage
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId
from pypnm_cmts.sgw.runtime_state import get_sgw_store
from pypnm_cmts.sgw.store import SgwCacheStore

CaptureExecutor = Callable[
    [CableModem, list[ChannelId], tuple[Inet, Inet], str, OperationRequestContextModel | None],
    list[tuple[ChannelId, MessageResponse]],
]


class ScQamSpectrumAnalyzerCaptureWorker(PnmCaptureWorkerBase):
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
        return "ScQamSpectrumAnalyzer"

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
            channel_ids=list(request_summary.channel_ids),
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
        channel_ids: list[ChannelId],
        request_context: OperationRequestContextModel | None,
    ) -> OperationStageResultModel:
        tftp_servers = PnmCaptureHelper.resolve_tftp_servers(request_context)
        tftp_path = PnmConfigManager.get_tftp_path()
        modem_ip = str(cable_modem.get_inet_address)
        tftp_log_key, tftp_log_value = PnmCaptureHelper.resolve_tftp_log_target(modem_ip=modem_ip, tftp_servers=tftp_servers)
        self.logger.info(
            "[CAPTURE_START] operation_id=%s sg_id=%s mac=%s ip=%s channel_count=%s %s=%s tftp_path=\"%s\"",
            short_op_id(operation_id),
            sg_id,
            mac_address,
            modem_ip,
            len(channel_ids),
            tftp_log_key,
            tftp_log_value,
            tftp_path,
        )
        capture_responses = self._capture_executor(cable_modem, channel_ids, tftp_servers, tftp_path, request_context)
        created_epoch = PnmCaptureHelper.now_epoch()

        final_transaction_ids: list[TransactionId] = []
        final_filenames: list[FileNameStr] = []
        final_message = CLEAR_MESSAGE
        status_code = ServiceStatusCode.SUCCESS

        if not capture_responses:
            status_code = ServiceStatusCode.FAILURE
            final_message = NO_MESSAGE_RESPONSE
        else:
            for _channel_id, capture_response in capture_responses:
                if capture_response is None:
                    status_code = ServiceStatusCode.FAILURE
                    final_message = NO_MESSAGE_RESPONSE
                    break
                if capture_response.status != ServiceStatusCode.SUCCESS:
                    status_code = capture_response.status
                    final_message = capture_response.status.name
                    break
                payload = capture_response.payload
                if not isinstance(payload, list):
                    status_code = ServiceStatusCode.FAILURE
                    final_message = MISSING_TRANSACTION_MESSAGE
                    break
                for element in payload:
                    message_type, message = PnmCaptureHelper.extract_payload_entry(element)
                    if message_type != MessageResponseType.PNM_FILE_TRANSACTION.name:
                        continue
                    if not isinstance(message, dict):
                        continue
                    transaction_id = message.get("transaction_id")
                    filename = message.get("filename")
                    if transaction_id is None or filename is None:
                        continue
                    final_transaction_ids.append(TransactionId(str(transaction_id)))
                    final_filenames.append(FileNameStr(str(filename)))

            if status_code == ServiceStatusCode.SUCCESS and (not final_transaction_ids or not final_filenames):
                status_code = ServiceStatusCode.PNM_FILE_TRANSACTION_ID_NOT_FOUND
                final_message = MISSING_TRANSACTION_MESSAGE

        self.logger.info(
            "[CAPTURE_RESULT] operation_id=%s sg_id=%s mac=%s status=%s message=\"%s\" tx_count=%s file_count=%s",
            short_op_id(operation_id),
            sg_id,
            mac_address,
            status_code.value,
            final_message,
            len(final_transaction_ids),
            len(final_filenames),
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


class ScQamSpectrumAnalyzerCaptureExecutor:
    """SCQAM SpectrumAnalyzer-specific capture executor helpers."""

    @staticmethod
    def run_pypnm_capture(
        cable_modem: CableModem,
        channel_ids: list[ChannelId],
        tftp_servers: tuple[Inet, Inet],
        _tftp_path: str,
        request_context: OperationRequestContextModel | None,
    ) -> list[tuple[ChannelId, MessageResponse]]:
        number_of_averages = 10
        resolution_bw = 25_000
        retrieval_type = int(SpectrumRetrievalType.FILE)

        if request_context is not None:
            if request_context.spectrum_analyzer_num_averages is not None:
                number_of_averages = int(request_context.spectrum_analyzer_num_averages)
            if request_context.spectrum_analyzer_resolution_bw is not None:
                resolution_bw = int(request_context.spectrum_analyzer_resolution_bw)
            if request_context.spectrum_analyzer_retrieval_type is not None:
                retrieval_type = int(request_context.spectrum_analyzer_retrieval_type)

        analyzer = DsScQamChannelSpectrumAnalyzer(
            cable_modem=cable_modem,
            tftp_servers=tftp_servers,
            number_of_averages=number_of_averages,
            resolution_bandwidth_hz=ResolutionBw(resolution_bw),
            channel_ids=channel_ids if channel_ids else None,
            spectrum_retrieval_type=SpectrumRetrievalType(retrieval_type),
        )
        return PnmAsyncioRunner.run_on_isolated_event_loop(analyzer.start())


class ScQamSpectrumAnalyzerServiceGroupOperationService(PnmServiceGroupOperationServiceBase):
    """Service layer for SG-level SCQAM SpectrumAnalyzer operation lifecycle endpoints."""

    def __init__(
        self,
        store: OperationStore | None = None,
        runner: OperationRunner | None = None,
        capture_executor: CaptureExecutor | None = None,
        precheck_executor: PrecheckExecutor | None = None,
        sgw_store: SgwCacheStore | None = None,
        max_inline_records: int = DEFAULT_MAX_INLINE_RECORDS,
    ) -> None:
        super().__init__(
            store=store,
            sgw_store=sgw_store,
            runtime_store_loader=lambda: get_sgw_store(),
            max_inline_records=max_inline_records,
        )
        self._capture_executor = capture_executor or ScQamSpectrumAnalyzerCaptureExecutor.run_pypnm_capture
        self._precheck_executor = precheck_executor or self._run_precheck
        if runner is None:
            worker = ScQamSpectrumAnalyzerCaptureWorker(
                store=self._store,
                capture_executor=self._capture_executor,
                precheck_executor=self._precheck_executor,
                sgw_store=self._sgw_store,
            )
            runner = OperationRunner(self._store, worker=worker)
        self._runner = runner

    def _log_start_capture(self, state: OperationStateModel) -> None:
        self.logger.info(
            build_start_capture_queued_log(
                operation_name="ScQamSpectrumAnalyzer",
                operation_id=state.operation_id,
                scope_sg_count=len(state.request_summary.serving_group_ids),
                scope_mac_count=len(state.request_summary.mac_addresses),
            )
        )

    @staticmethod
    def _build_request_context(
        request: ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest,
    ) -> OperationRequestContextModel:
        cmts = request.cmts
        pnm = cmts.cable_modem.pnm_parameters
        tftp = pnm.tftp if pnm is not None else None
        snmp = cmts.cable_modem.snmp
        snmp_v2c = snmp.snmpV2C if snmp is not None else None
        capture_settings = request.capture_settings
        return OperationRequestContextModel(
            tftp_ipv4=tftp.ipv4 if tftp is not None else None,
            tftp_ipv6=tftp.ipv6 if tftp is not None else None,
            snmp_write_community=snmp_v2c.community if snmp_v2c is not None else None,
            spectrum_analyzer_num_averages=capture_settings.number_of_averages,
            spectrum_analyzer_resolution_bw=int(capture_settings.resolution_bandwidth_hz),
            spectrum_analyzer_retrieval_type=int(capture_settings.spectrum_retrieval_type),
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
        request: ScQamSpectrumAnalyzerServiceGroupOperationRequest,
    ) -> PnmCaptureOperationId:
        return request.pnm_capture_operation_id

    @staticmethod
    def _build_start_response(
        state: OperationStateModel,
    ) -> ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse:
        return ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse(
            status=ServiceStatusCode.SUCCESS,
            message="",
            operation=state,
        )

    @staticmethod
    def _build_status_response(
        status: ServiceStatusCode,
        message: str,
        state: OperationStateModel | None,
    ) -> ScQamSpectrumAnalyzerServiceGroupStatusResponse:
        return ScQamSpectrumAnalyzerServiceGroupStatusResponse(
            status=status,
            message=message,
            operation=state,
        )

    @staticmethod
    def _build_cancel_response(
        status: ServiceStatusCode,
        message: str,
        state: OperationStateModel | None,
    ) -> ScQamSpectrumAnalyzerServiceGroupCancelResponse:
        return ScQamSpectrumAnalyzerServiceGroupCancelResponse(
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
    ) -> ScQamSpectrumAnalyzerServiceGroupResultsResponse:
        return ScQamSpectrumAnalyzerServiceGroupResultsResponse(
            status=status,
            message=message,
            summary=summary,
            records=records,
        )

    def _build_request_summary(
        self,
        request: ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest,
    ) -> OperationRequestSummaryModel:
        cmts = request.cmts
        channel_ids = ScQamSpectrumAnalyzerServiceGroupOperationService._resolve_channel_ids(cmts)
        requested_sg_ids = list(cmts.serving_group.id)
        requested_mac_addresses = list(cmts.cable_modem.mac_address)
        serving_group_ids, mac_addresses = self._resolve_modem_scope(requested_sg_ids, requested_mac_addresses)
        self.logger.info(
            build_request_scope_log(
                operation_name="ScQamSpectrumAnalyzer",
                requested_sg_count=len(requested_sg_ids),
                requested_mac_count=len(requested_mac_addresses),
                resolved_sg_count=len(serving_group_ids),
                resolved_mac_count=len(mac_addresses),
                channel_count=len(channel_ids),
            )
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

    @staticmethod
    def _resolve_channel_ids(cmts: CmtsRequestEnvelopeModel) -> list[ChannelId]:
        pnm = cmts.cable_modem.pnm_parameters
        capture = pnm.capture if pnm is not None else None
        channel_ids = capture.channel_ids if capture is not None else None
        if not channel_ids:
            return []
        return list(channel_ids)


__all__ = [
    "ScQamSpectrumAnalyzerServiceGroupOperationService",
]

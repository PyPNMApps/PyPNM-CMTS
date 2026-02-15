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
from pypnm.api.routes.docs.pnm.ds.histogram.service import CmDsHistogramService
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.docsis.cable_modem import CableModem
from pypnm.lib.inet import Inet
from pypnm.lib.types import (
    FileNameStr,
    InetAddressStr,
    MacAddressStr,
    TransactionId,
)

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
from pypnm_cmts.api.common.service.pnm.modem import PnmModemResolver
from pypnm_cmts.api.common.service.pnm.operation_service import (
    DEFAULT_MAX_INLINE_RECORDS,
    PnmServiceGroupOperationServiceBase,
)
from pypnm_cmts.api.routes.pnm.sg.ds.histogram.schemas import (
    DsHistogramServiceGroupCancelResponse,
    DsHistogramServiceGroupOperationRequest,
    DsHistogramServiceGroupResultsResponse,
    DsHistogramServiceGroupStartCaptureRequest,
    DsHistogramServiceGroupStartCaptureResponse,
    DsHistogramServiceGroupStatusResponse,
)
from pypnm_cmts.lib.constants import OperationStage
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
            operation_id,
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
            "[CAPTURE_RESULT] operation_id=%s sg_id=%s mac=%s status=%s message=%s tx_id=%s filename=%s",
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

    def _log_start_capture(self, state: OperationStateModel) -> None:
        self.logger.info(
            "DsHistogram-StartCapture [QUEUED] operation_id=%s, scope_sg=%s, scope_macs=%s",
            state.operation_id,
            len(state.request_summary.serving_group_ids),
            len(state.request_summary.mac_addresses),
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
        request: DsHistogramServiceGroupOperationRequest,
    ) -> PnmCaptureOperationId:
        return request.pnm_capture_operation_id

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

    def _build_request_summary(
        self,
        request: DsHistogramServiceGroupStartCaptureRequest,
    ) -> OperationRequestSummaryModel:
        cmts = request.cmts
        requested_sg_ids = list(cmts.serving_group.id)
        requested_mac_addresses = list(cmts.cable_modem.mac_address)
        serving_group_ids, mac_addresses = self._resolve_modem_scope(requested_sg_ids, requested_mac_addresses)
        self.logger.info(
            "ds_histogram request scope requested_sg=%s requested_macs=%s resolved_sg=%s resolved_macs=%s",
            len(requested_sg_ids),
            len(requested_mac_addresses),
            len(serving_group_ids),
            len(mac_addresses),
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

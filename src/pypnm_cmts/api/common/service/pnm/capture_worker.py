# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.docsis.cable_modem import CableModem
from pypnm.lib.types import InetAddressStr, MacAddressStr

from pypnm_cmts.api.common.operations.logging import short_op_id
from pypnm_cmts.api.common.operations.models import (
    OperationRequestContextModel,
    OperationRequestSummaryModel,
    OperationStageResultModel,
)
from pypnm_cmts.api.common.operations.runner import (
    OperationWorkerResultModel,
    OperationWorkItemModel,
)
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.common.service.pnm.capture import PnmCaptureHelper
from pypnm_cmts.api.common.service.pnm.constants import MISSING_IP_MESSAGE
from pypnm_cmts.api.common.service.pnm.modem import PnmModemResolver
from pypnm_cmts.lib.constants import OperationStage
from pypnm_cmts.lib.types import ServiceGroupId

PrecheckExecutor = Callable[[CableModem], tuple[ServiceStatusCode, str]]


class PnmCaptureWorkerBase(ABC):
    """Shared per-modem worker flow for eligibility, precheck, and capture stages."""

    def __init__(
        self,
        store: OperationStore,
        precheck_executor: PrecheckExecutor,
    ) -> None:
        self._store = store
        self._precheck_executor = precheck_executor
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def __call__(self, item: OperationWorkItemModel) -> OperationWorkerResultModel:
        """Execute eligibility, precheck, and capture stages for a modem work item."""
        self.logger.info(
            "[START] operation_id=%s, sg_id=%s, mac=%s, attempt=%s",
            short_op_id(item.operation_id),
            item.sg_id,
            item.mac_address,
            item.attempt,
        )
        state = self._store.load_state(item.operation_id)
        request_summary = state.request_summary
        request_context = self._store.load_request_context(item.operation_id)
        ip_address = self._resolve_modem_ip(item.sg_id, item.mac_address)
        now_epoch = PnmCaptureHelper.now_epoch()
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
                "[ELIGIBILITY_FAILED] operation_id=%s sg_id=%s mac=%s status=%s message=%s",
                short_op_id(item.operation_id),
                item.sg_id,
                item.mac_address,
                eligibility_result.status_code.value,
                eligibility_result.message,
            )
            return OperationWorkerResultModel(ip_address=ip_address, stages=stages)

        write_community = PnmModemResolver.resolve_write_community(request_context)
        community_source = "request_override"
        if request_context is None or request_context.snmp_write_community is None:
            community_source = "system_default"
        precheck_cm = PnmModemResolver.build_cable_modem(
            mac_address=item.mac_address,
            ip_address=ip_address,
            write_community=write_community,
        )
        self.logger.info(
            "[PRECHECK_START] operation_id=%s sg_id=%s mac=%s ip=%s community_source=%s%s",
            short_op_id(item.operation_id),
            item.sg_id,
            item.mac_address,
            ip_address,
            community_source,
            f" community={write_community}" if self.logger.isEnabledFor(logging.DEBUG) else "",
        )
        precheck_status, precheck_message = self._precheck_executor(precheck_cm)
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
                "[PRECHECK_FAILED] operation_id=%s sg_id=%s mac=%s status=%s message=%s",
                short_op_id(item.operation_id),
                item.sg_id,
                item.mac_address,
                precheck_status.value,
                precheck_message,
            )
            return OperationWorkerResultModel(ip_address=ip_address, stages=stages)

        # Use a fresh CableModem for capture because precheck can close loop-bound transports.
        capture_cm = PnmModemResolver.build_cable_modem(
            mac_address=item.mac_address,
            ip_address=ip_address,
            write_community=write_community,
        )
        capture_result = self._run_capture_stage(
            item=item,
            request_summary=request_summary,
            request_context=request_context,
            cable_modem=capture_cm,
        )
        stages.append(capture_result)
        self.logger.info(
            "[COMPLETE] operation_id=%s sg_id=%s mac=%s status=%s message=%s tx_count=%s file_count=%s",
            short_op_id(item.operation_id),
            item.sg_id,
            item.mac_address,
            capture_result.status_code.value,
            capture_result.message,
            len(capture_result.transaction_ids),
            len(capture_result.filenames),
        )
        return OperationWorkerResultModel(ip_address=ip_address, stages=stages)

    @property
    @abstractmethod
    def _worker_log_prefix(self) -> str:
        """Operation-specific log prefix."""

    @abstractmethod
    def _resolve_modem_ip(
        self,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
    ) -> InetAddressStr | None:
        """Resolve the modem management IP for a work item."""

    @abstractmethod
    def _run_capture_stage(
        self,
        item: OperationWorkItemModel,
        request_summary: OperationRequestSummaryModel,
        request_context: OperationRequestContextModel | None,
        cable_modem: CableModem,
    ) -> OperationStageResultModel:
        """Execute operation-specific capture stage logic."""


__all__ = [
    "PnmCaptureWorkerBase",
    "PrecheckExecutor",
]

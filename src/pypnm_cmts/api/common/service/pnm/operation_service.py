# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from weakref import WeakSet

from fastapi import HTTPException, status
from pydantic import BaseModel
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import ChannelId, MacAddressStr

from pypnm_cmts.api.common.operations.logging import short_op_id
from pypnm_cmts.api.common.operations.models import (
    OperationRequestContextModel,
    OperationRequestSummaryModel,
    OperationResultsSummaryModel,
    OperationStateModel,
    PerModemLinkageRecordModel,
)
from pypnm_cmts.api.common.operations.runner import OperationRunner
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.common.service.pnm.scope import (
    PnmOperationScopeResolver,
    RuntimeStoreLoader,
)
from pypnm_cmts.lib.constants import OperationState, RfChannelType
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId
from pypnm_cmts.sgw.runtime_state import get_sgw_store
from pypnm_cmts.sgw.store import SgwCacheStore

DEFAULT_MAX_INLINE_RECORDS = 250
NOT_FOUND_MESSAGE = "operation not found"


class PnmServiceGroupOperationServiceBase(ABC):
    """Reusable SG-level operation lifecycle and scope resolution helpers."""

    _registry: WeakSet[PnmServiceGroupOperationServiceBase] = WeakSet()

    def __init__(
        self,
        store: OperationStore | None = None,
        sgw_store: SgwCacheStore | None = None,
        runtime_store_loader: RuntimeStoreLoader | None = None,
        max_inline_records: int = DEFAULT_MAX_INLINE_RECORDS,
    ) -> None:
        self._store = store or OperationStore()
        self._sgw_store = sgw_store
        loader = runtime_store_loader or (lambda: get_sgw_store())
        self._scope_resolver = PnmOperationScopeResolver(
            sgw_store=self._sgw_store,
            runtime_store_loader=loader,
        )
        self._runner: OperationRunner | None = None
        self._max_inline_records = max_inline_records
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._registry.add(self)

    def start_capture(self, request: BaseModel) -> BaseModel:
        """Create a new SG-level operation and start background execution."""
        request_summary = self._build_request_summary(request)
        request_context = self._build_request_context(request)
        state = self._store.create_operation(request_summary, request_context)
        self._log_start_capture(state)
        runner = self._runner
        if runner is None:
            raise RuntimeError("operation runner is not configured")
        started = runner.start(state.operation_id)
        if not started:
            self.logger.warning("Operation-Runner already active for %s", state.operation_id)
        return self._build_start_response(state)

    def status(self, request: BaseModel) -> BaseModel:
        """Return persisted operation state."""
        operation_id = self._extract_operation_id(request)
        status, message, state = self._load_operation_state(operation_id)
        return self._build_status_response(status, message, state)

    def cancel(self, request: BaseModel) -> BaseModel:
        """Request cancellation for an operation."""
        operation_id = self._extract_operation_id(request)
        status, message, state = self._cancel_operation(operation_id)
        return self._build_cancel_response(status, message, state)

    def results(self, request: BaseModel) -> BaseModel:
        """Return operation linkage results when available."""
        operation_id = self._extract_operation_id(request)
        status, message, summary, records = self._load_operation_results(operation_id)
        return self._build_results_response(status, message, summary, records)

    def _load_operation_state(
        self,
        operation_id: PnmCaptureOperationId,
    ) -> tuple[ServiceStatusCode, str, OperationStateModel | None]:
        try:
            state = self._store.load_state(operation_id)
        except FileNotFoundError:
            return (ServiceStatusCode.FAILURE, NOT_FOUND_MESSAGE, None)
        message = ""
        if state.state == OperationState.COMPLETED and state.counters.total_modems == 0:
            message = "no modems selected"
        return (ServiceStatusCode.SUCCESS, message, state)

    def _cancel_operation(
        self,
        operation_id: PnmCaptureOperationId,
    ) -> tuple[ServiceStatusCode, str, OperationStateModel | None]:
        runner = self._runner
        if runner is None:
            raise RuntimeError("operation runner is not configured")
        try:
            state = runner.request_cancel(operation_id)
        except FileNotFoundError:
            return (ServiceStatusCode.FAILURE, NOT_FOUND_MESSAGE, None)
        return (ServiceStatusCode.SUCCESS, "", state)

    def _load_operation_results(
        self,
        operation_id: PnmCaptureOperationId,
    ) -> tuple[ServiceStatusCode, str, OperationResultsSummaryModel, list[PerModemLinkageRecordModel]]:
        try:
            self._store.load_state(operation_id)
        except FileNotFoundError:
            return (
                ServiceStatusCode.FAILURE,
                NOT_FOUND_MESSAGE,
                OperationResultsSummaryModel(),
                [],
            )

        files_scanned = self._store.count_result_files(operation_id)
        total_records = self._store.count_result_records(operation_id)
        include_records = total_records <= self._max_inline_records
        records: list[PerModemLinkageRecordModel] = []
        if include_records:
            records = self._store.load_result_records(operation_id)
        summary = OperationResultsSummaryModel(
            record_count=total_records,
            included_count=len(records),
            files_scanned=files_scanned,
        )
        message = "" if total_records > 0 else "no results recorded"
        return (ServiceStatusCode.SUCCESS, message, summary, records)

    def _resolve_modem_scope(
        self,
        requested_sg_ids: list[ServiceGroupId],
        requested_mac_addresses: list[MacAddressStr],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        scope = self._scope_resolver.resolve_modem_scope(requested_sg_ids, requested_mac_addresses)
        resolved_store = self._scope_resolver.get_store()
        if self._sgw_store is None and resolved_store is not None:
            self._sgw_store = resolved_store
        return scope

    def _validate_requested_downstream_ofdm_channel_ids(
        self,
        requested_channel_ids: list[ChannelId],
        serving_group_ids: list[ServiceGroupId],
    ) -> None:
        """Reject requested downstream OFDM channel ids not present in SGW inventory."""
        if not requested_channel_ids or not serving_group_ids:
            return

        store = self._scope_resolver.resolve_store()
        if store is None:
            return
        if self._sgw_store is None:
            self._sgw_store = store

        valid_channel_ids: list[ChannelId] = []
        for sg_id in serving_group_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                continue
            for channel in entry.snapshot.ds_rf_channels:
                if channel.channel_type != RfChannelType.OFDM:
                    continue
                candidate = ChannelId(int(channel.channel_id))
                if candidate not in valid_channel_ids:
                    valid_channel_ids.append(candidate)

        if not valid_channel_ids:
            return

        invalid_channel_ids = [
            channel_id for channel_id in requested_channel_ids if channel_id not in valid_channel_ids
        ]
        if not invalid_channel_ids:
            return

        detail = (
            "cmts.cable_modem.pnm_parameters.capture.channel_ids contains invalid downstream OFDM "
            f"channel ids: {[int(channel_id) for channel_id in invalid_channel_ids]}. "
            f"Valid ids for the selected serving groups: {[int(channel_id) for channel_id in valid_channel_ids]}"
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    def _log_start_capture(self, state: OperationStateModel) -> None:
        self.logger.info(
            "Operation-Start [QUEUED] operation_id=%s, scope_sg=%s, scope_macs=%s",
            short_op_id(state.operation_id),
            len(state.request_summary.serving_group_ids),
            len(state.request_summary.mac_addresses),
        )

    @classmethod
    def get_registered_services(cls) -> list[PnmServiceGroupOperationServiceBase]:
        """Return live registered PNM operation service instances."""
        return list(cls._registry)

    def get_debug_stats(self) -> dict[str, int | str]:
        """Return lightweight in-memory debug counters for this service instance."""
        runner_stats = {
            "thread_count": 0,
            "alive_thread_count": 0,
            "tracked_operation_count": 0,
            "total_pending_futures": 0,
            "total_abandoned_futures": 0,
            "total_retry_queue_items": 0,
            "total_queue_items": 0,
        }
        if self._runner is not None:
            runner_stats = self._runner.get_debug_stats()
        return {
            "service_name": self.__class__.__name__,
            "thread_count": int(runner_stats["thread_count"]),
            "alive_thread_count": int(runner_stats["alive_thread_count"]),
            "tracked_operation_count": int(runner_stats["tracked_operation_count"]),
            "total_pending_futures": int(runner_stats["total_pending_futures"]),
            "total_abandoned_futures": int(runner_stats["total_abandoned_futures"]),
            "total_retry_queue_items": int(runner_stats["total_retry_queue_items"]),
            "total_queue_items": int(runner_stats["total_queue_items"]),
        }

    @abstractmethod
    def _build_request_summary(self, request: BaseModel) -> OperationRequestSummaryModel:
        """Build operation request summary from endpoint request payload."""

    @abstractmethod
    def _build_request_context(self, request: BaseModel) -> OperationRequestContextModel:
        """Build operation request context from endpoint request payload."""

    @abstractmethod
    def _extract_operation_id(self, request: BaseModel) -> PnmCaptureOperationId:
        """Extract operation identifier from request payload."""

    @abstractmethod
    def _build_start_response(self, state: OperationStateModel) -> BaseModel:
        """Build start response model."""

    @abstractmethod
    def _build_status_response(
        self,
        status: ServiceStatusCode,
        message: str,
        state: OperationStateModel | None,
    ) -> BaseModel:
        """Build status response model."""

    @abstractmethod
    def _build_cancel_response(
        self,
        status: ServiceStatusCode,
        message: str,
        state: OperationStateModel | None,
    ) -> BaseModel:
        """Build cancel response model."""

    @abstractmethod
    def _build_results_response(
        self,
        status: ServiceStatusCode,
        message: str,
        summary: OperationResultsSummaryModel,
        records: list[PerModemLinkageRecordModel],
    ) -> BaseModel:
        """Build results response model."""


__all__ = [
    "DEFAULT_MAX_INLINE_RECORDS",
    "NOT_FOUND_MESSAGE",
    "PnmServiceGroupOperationServiceBase",
]

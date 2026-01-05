# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import CacheRefreshMode
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)
from pypnm_cmts.sgw.metrics import NoOpSgwMetrics, SgwMetrics
from pypnm_cmts.sgw.models import (
    DEFAULT_AGE_SECONDS,
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwRefreshErrorModel,
    SgwRefreshResultModel,
    SgwSnapshotModel,
    SgwSnapshotPayloadModel,
)
from pypnm_cmts.sgw.store import SgwCacheStore

JITTER_MIN_SECONDS = 0
REFRESH_MODE_NONE = "none"
REFRESH_MODE_HEAVY = "heavy"
REFRESH_MODE_LIGHT = "light"
REFRESH_RESULT_OK = "ok"
REFRESH_RESULT_ERROR = "error"
REFRESH_RESULT_STALE = "stale"

HeavyPoller = Callable[[ServiceGroupId, CmtsOrchestratorSettings], SgwSnapshotPayloadModel]
LightPoller = Callable[[ServiceGroupId, CmtsOrchestratorSettings, list[SgwCableModemModel]], list[SgwCableModemModel]]
Clock = Callable[[], float]


class SgwManager:
    """Serving group worker cache manager."""

    def __init__(
        self,
        settings: CmtsOrchestratorSettings,
        store: SgwCacheStore | None = None,
        service_groups: list[ServiceGroupId] | None = None,
        jitter_provider: Callable[[ServiceGroupId, int], int] | None = None,
        heavy_poller: HeavyPoller | None = None,
        light_poller: LightPoller | None = None,
        metrics: SgwMetrics | None = None,
    ) -> None:
        """
        Initialize the SGW manager.

        Args:
            settings (CmtsOrchestratorSettings): Orchestrator settings instance.
            store (SgwCacheStore | None): Optional cache store.
            service_groups (list[ServiceGroupId] | None): Initial service group identifiers.
            jitter_provider (Callable[[ServiceGroupId, int], int] | None): Optional jitter provider.
            heavy_poller (HeavyPoller | None): Optional heavy refresh poller.
            light_poller (LightPoller | None): Optional light refresh poller.
            metrics (SgwMetrics | None): Optional metrics sink.
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._settings = settings
        self._store = store if store is not None else SgwCacheStore()
        self._service_groups = list(service_groups) if service_groups is not None else []
        self._jitter_provider = jitter_provider if jitter_provider is not None else self._default_jitter
        self._heavy_poller = heavy_poller if heavy_poller is not None else self._default_heavy_poller
        self._light_poller = light_poller if light_poller is not None else self._default_light_poller
        self._metrics = metrics if metrics is not None else NoOpSgwMetrics()
        self._jitter_by_sg: dict[ServiceGroupId, int] = {}
        self._refresh_requests: dict[ServiceGroupId, CacheRefreshMode] = {}
        self._stop_requested = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        if self._service_groups:
            self._initialize_jitter(self._service_groups)

    def set_service_groups(self, service_groups: list[ServiceGroupId]) -> None:
        """Update the service groups managed by this instance."""
        with self._lock:
            self._service_groups = list(service_groups)
            self._initialize_jitter(self._service_groups)

    def get_service_groups(self) -> list[ServiceGroupId]:
        """Return the current list of service groups managed by this manager."""
        with self._lock:
            return list(self._service_groups)

    def get_store(self) -> SgwCacheStore:
        """
        Return the cache store associated with this manager.
        """
        return self._store

    def stop(self) -> None:
        """Request that the refresh loop stop."""
        with self._lock:
            self._stop_requested = True
            self._stop_event.set()

    def reset_stop(self) -> None:
        """
        Clear stop flags to allow the refresh loop to restart.
        """
        with self._lock:
            self._stop_requested = False
            self._stop_event.clear()

    def request_refresh(
        self,
        sg_id: ServiceGroupId,
        mode: CacheRefreshMode,
        now_epoch: float,
    ) -> tuple[bool, str]:
        """
        Request an on-demand refresh for a service group.

        Returns:
            tuple[bool, str]: (accepted, message)
        """
        if mode == CacheRefreshMode.NONE:
            return (False, "")
        with self._lock:
            if sg_id not in self._service_groups:
                return (False, "sg_id not managed by sgw")
            if mode == CacheRefreshMode.HEAVY and self._heavy_refresh_rate_limited(sg_id, now_epoch):
                return (False, "heavy refresh rate limited")
            current = self._refresh_requests.get(sg_id)
            if current == CacheRefreshMode.HEAVY:
                return (True, "")
            if mode == CacheRefreshMode.HEAVY or current is None:
                self._refresh_requests[sg_id] = mode
                return (True, "")
        return (True, "")

    def refresh_forever(
        self,
        clock: Clock | None = None,
        max_cycles: int | None = None,
    ) -> list[SgwRefreshResultModel]:
        """
        Execute refresh cycles until stopped or max_cycles is reached.

        Args:
            clock (Clock | None): Optional clock function for tests.
            max_cycles (int | None): Optional maximum number of cycles to execute.

        Returns:
            list[SgwRefreshResultModel]: Collected refresh results when max_cycles is provided.
        """
        if max_cycles is not None and int(max_cycles) < 0:
            raise ValueError("max_cycles must be non-negative.")
        clock_fn = clock if clock is not None else self._default_clock
        interval_seconds = float(self._settings.sgw.poll_light_seconds)
        results: list[SgwRefreshResultModel] = []
        cycles = 0

        # Hardening: preserve any pre-existing stop signal by checking and
        # clearing state under the same lock to avoid races with `stop()`.
        with self._lock:
            pre_stop = bool(self._stop_event.is_set()) or bool(self._stop_requested)
            if pre_stop:
                return results
            # Normal startup: ensure flags are cleared for a fresh run.
            self._stop_requested = False
            self._stop_event.clear()

        while not self._stop_requested:
            now_epoch = float(clock_fn())
            result = self.refresh_once(now_epoch)
            if max_cycles is not None:
                results.append(result)
            cycles += 1
            if max_cycles is not None and cycles >= int(max_cycles):
                break
            if self._stop_requested:
                break
            if self._stop_event.wait(timeout=interval_seconds):
                break
        return results

    def refresh_once(self, now_epoch: float) -> SgwRefreshResultModel:
        """
        Execute a single refresh cycle.

        Args:
            now_epoch (float): Current time in epoch seconds.

        Returns:
            SgwRefreshResultModel: Summary of refresh operations performed.
        """
        if float(now_epoch) < 0:
            raise ValueError("now_epoch must be non-negative.")
        if not bool(self._settings.sgw.enabled):
            return SgwRefreshResultModel(snapshot_time_epoch=float(now_epoch))

        heavy_refreshed: list[ServiceGroupId] = []
        light_refreshed: list[ServiceGroupId] = []
        errors: list[SgwRefreshErrorModel] = []
        with self._lock:
            service_groups = list(self._service_groups)

        for sg_id in service_groups:
            entry = self._ensure_entry(sg_id, now_epoch)
            metadata = entry.snapshot.metadata
            jitter_seconds = self._resolve_jitter_seconds(sg_id)
            refresh_mode = REFRESH_MODE_NONE
            refresh_applied = False
            error_message = ""
            start_time = self._monotonic()

            try:
                with self._lock:
                    requested = self._refresh_requests.pop(sg_id, None)
                heavy_due = False
                light_due = False
                if requested == CacheRefreshMode.HEAVY:
                    heavy_due = True
                elif requested == CacheRefreshMode.LIGHT:
                    light_due = True
                else:
                    heavy_due = self._is_refresh_due(
                        metadata.last_heavy_refresh_epoch,
                        int(self._settings.sgw.poll_heavy_seconds),
                        jitter_seconds,
                        now_epoch,
                    )
                    if not heavy_due:
                        light_due = self._is_refresh_due(
                            metadata.last_light_refresh_epoch,
                            int(self._settings.sgw.poll_light_seconds),
                            jitter_seconds,
                            now_epoch,
                    )
                if heavy_due:
                    refresh_mode = REFRESH_MODE_HEAVY
                    payload = self._heavy_poller(sg_id, self._settings)
                    self._refresh_heavy(sg_id, now_epoch, payload)
                    heavy_refreshed.append(sg_id)
                    light_refreshed.append(sg_id)
                    refresh_applied = True
                elif light_due:
                    refresh_mode = REFRESH_MODE_LIGHT
                    updated_modems = self._light_poller(
                        sg_id,
                        self._settings,
                        list(entry.snapshot.cable_modems),
                    )
                    merged_modems = self._merge_light_updates(
                        list(entry.snapshot.cable_modems),
                        list(updated_modems),
                    )
                    self._refresh_light(sg_id, now_epoch, merged_modems)
                    light_refreshed.append(sg_id)
                    refresh_applied = True
            except Exception as exc:
                error_message = self._normalize_error_message(str(exc))
                metadata = self._store.mark_error(sg_id, error_message, now_epoch)
                errors.append(SgwRefreshErrorModel(sg_id=sg_id, message=metadata.last_error or ""))

            entry = self._store.get_entry(sg_id) or entry
            metadata = entry.snapshot.metadata
            age_seconds = max(DEFAULT_AGE_SECONDS, float(now_epoch) - float(metadata.snapshot_time_epoch))
            metadata = metadata.model_copy(update={"age_seconds": age_seconds})

            stale = False
            if metadata.refresh_state != SgwRefreshState.ERROR:
                if self._store.compute_staleness(age_seconds, int(self._settings.sgw.cache_max_age_seconds)):
                    stale = True
                    metadata = metadata.model_copy(update={"refresh_state": SgwRefreshState.STALE})
                else:
                    metadata = metadata.model_copy(update={"refresh_state": SgwRefreshState.OK})

            entry.snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
            self._store.upsert_entry(entry)

            duration_ms = max(0.0, (self._monotonic() - start_time) * 1000.0)
            if refresh_mode != REFRESH_MODE_NONE and (refresh_applied or error_message != "" or stale):
                self._metrics.record_refresh_duration(refresh_mode, duration_ms)
            if error_message != "" and refresh_mode != REFRESH_MODE_NONE:
                self._metrics.increment_refresh_error(refresh_mode)
            if stale:
                self._metrics.increment_staleness()
            if refresh_applied or error_message != "" or stale:
                result = REFRESH_RESULT_OK
                if error_message != "":
                    result = REFRESH_RESULT_ERROR
                elif stale:
                    result = REFRESH_RESULT_STALE
                interval_seconds = 0.0
                if refresh_mode == REFRESH_MODE_HEAVY:
                    interval_seconds = float(self._settings.sgw.poll_heavy_seconds)
                elif refresh_mode == REFRESH_MODE_LIGHT:
                    interval_seconds = float(self._settings.sgw.poll_light_seconds)
                self._log_refresh_event(
                    sg_id=sg_id,
                    refresh_mode=refresh_mode,
                    duration_ms=duration_ms,
                    result=result,
                    snapshot_time_epoch=float(metadata.snapshot_time_epoch),
                    age_seconds=float(metadata.age_seconds),
                    interval_seconds=interval_seconds,
                    error_message=error_message,
                )

        return SgwRefreshResultModel(
            snapshot_time_epoch=float(now_epoch),
            heavy_refreshed_sg_ids=heavy_refreshed,
            light_refreshed_sg_ids=light_refreshed,
            errors=errors,
        )

    def _ensure_entry(self, sg_id: ServiceGroupId, now_epoch: float) -> SgwCacheEntryModel:
        entry = self._store.get_entry(sg_id)
        if entry is not None:
            return entry
        metadata = SgwCacheMetadataModel(
            snapshot_time_epoch=float(now_epoch),
            age_seconds=DEFAULT_AGE_SECONDS,
        )
        snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
        entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)
        self._store.upsert_entry(entry)
        return entry

    def _refresh_heavy(
        self,
        sg_id: ServiceGroupId,
        now_epoch: float,
        payload: SgwSnapshotPayloadModel,
    ) -> None:
        entry = self._ensure_entry(sg_id, now_epoch)
        metadata = entry.snapshot.metadata.model_copy(
            update={
                "snapshot_time_epoch": float(now_epoch),
                "age_seconds": DEFAULT_AGE_SECONDS,
                "last_heavy_refresh_epoch": float(now_epoch),
                "last_light_refresh_epoch": float(now_epoch),
                "refresh_state": SgwRefreshState.OK,
                "last_error": None,
            }
        )
        entry.snapshot = entry.snapshot.model_copy(
            update={
                "ds_ch_set_id": payload.ds_ch_set_id,
                "us_ch_set_id": payload.us_ch_set_id,
                "ds_channels": payload.ds_channels,
                "us_channels": payload.us_channels,
                "ds_rf_channels": list(payload.ds_rf_channels),
                "us_rf_channels": list(payload.us_rf_channels),
                "cable_modems": list(payload.cable_modems),
                "metadata": metadata,
            }
        )
        self._store.upsert_entry(entry)

    def _refresh_light(
        self,
        sg_id: ServiceGroupId,
        now_epoch: float,
        cable_modems: list[SgwCableModemModel],
    ) -> None:
        entry = self._ensure_entry(sg_id, now_epoch)
        metadata = entry.snapshot.metadata.model_copy(
            update={
                "snapshot_time_epoch": float(now_epoch),
                "age_seconds": DEFAULT_AGE_SECONDS,
                "last_light_refresh_epoch": float(now_epoch),
                "refresh_state": SgwRefreshState.OK,
                "last_error": None,
            }
        )
        entry.snapshot = entry.snapshot.model_copy(
            update={
                "cable_modems": list(cable_modems),
                "metadata": metadata,
            }
        )
        self._store.upsert_entry(entry)

    def _log_refresh_event(
        self,
        sg_id: ServiceGroupId,
        refresh_mode: str,
        duration_ms: float,
        result: str,
        snapshot_time_epoch: float,
        age_seconds: float,
        interval_seconds: float,
        error_message: str,
    ) -> None:
        worker_id = self._format_worker_id(sg_id)
        if error_message != "":
            self.logger.warning(
                "sgw refresh error SGWorkerID: %s",
                worker_id,
                extra={
                    "sg_id": int(sg_id),
                    "worker_id": worker_id,
                    "refresh_mode": refresh_mode,
                    "duration_ms": duration_ms,
                    "result": result,
                    "snapshot_time_epoch": snapshot_time_epoch,
                    "age_seconds": age_seconds,
                    "interval_seconds": interval_seconds,
                    "error_message": error_message,
                },
            )
            return
        self.logger.info(
            "sgw refresh SGWorkerID: %s",
            worker_id,
            extra={
                "sg_id": int(sg_id),
                "worker_id": worker_id,
                "refresh_mode": refresh_mode,
                "duration_ms": duration_ms,
                "result": result,
                "snapshot_time_epoch": snapshot_time_epoch,
                "age_seconds": age_seconds,
                "interval_seconds": interval_seconds,
            },
        )

    @staticmethod
    def _format_worker_id(sg_id: ServiceGroupId) -> str:
        return f"sgw-{int(sg_id)}"

    @staticmethod
    def _normalize_error_message(message: str) -> str:
        trimmed = message.strip()
        if trimmed == "":
            return ""
        return trimmed[:SGW_LAST_ERROR_MAX_LENGTH]

    @staticmethod
    def _monotonic() -> float:
        return float(time.monotonic())

    @staticmethod
    def _merge_light_updates(
        existing_modems: list[SgwCableModemModel],
        updated_modems: list[SgwCableModemModel],
    ) -> list[SgwCableModemModel]:
        if not updated_modems:
            return [modem.model_copy(deep=True) for modem in existing_modems]
        updated_by_mac = {str(modem.mac): modem for modem in updated_modems}
        merged: list[SgwCableModemModel] = []
        for modem in existing_modems:
            key = str(modem.mac)
            replacement = updated_by_mac.get(key)
            if replacement is None:
                merged.append(modem.model_copy(deep=True))
            else:
                merged.append(replacement.model_copy(deep=True))
        return merged

    def _is_refresh_due(
        self,
        last_refresh_epoch: float | None,
        interval_seconds: int,
        jitter_seconds: int,
        now_epoch: float,
    ) -> bool:
        if last_refresh_epoch is None:
            return True
        elapsed = float(now_epoch) - float(last_refresh_epoch)
        return elapsed >= float(interval_seconds + jitter_seconds)

    def _heavy_refresh_rate_limited(self, sg_id: ServiceGroupId, now_epoch: float) -> bool:
        entry = self._store.get_entry(sg_id)
        if entry is None:
            return False
        last_heavy = entry.snapshot.metadata.last_heavy_refresh_epoch
        if last_heavy is None:
            return False
        elapsed = float(now_epoch) - float(last_heavy)
        return elapsed < float(self._settings.sgw.poll_heavy_seconds)

    def _resolve_jitter_seconds(self, sg_id: ServiceGroupId) -> int:
        cached = self._jitter_by_sg.get(sg_id)
        if cached is not None:
            return cached
        max_jitter = int(self._settings.sgw.refresh_jitter_seconds)
        if max_jitter <= 0:
            self._jitter_by_sg[sg_id] = JITTER_MIN_SECONDS
            return JITTER_MIN_SECONDS
        jitter_value = int(self._jitter_provider(sg_id, max_jitter))
        jitter_value = self._clamp_jitter(jitter_value, max_jitter)
        self._jitter_by_sg[sg_id] = jitter_value
        return jitter_value

    @staticmethod
    def _default_jitter(_sg_id: ServiceGroupId, max_jitter_seconds: int) -> int:
        if max_jitter_seconds <= 0:
            return JITTER_MIN_SECONDS
        return random.randint(JITTER_MIN_SECONDS, max_jitter_seconds)

    @staticmethod
    def _default_heavy_poller(
        _sg_id: ServiceGroupId,
        _settings: CmtsOrchestratorSettings,
    ) -> SgwSnapshotPayloadModel:
        return SgwSnapshotPayloadModel()

    @staticmethod
    def _default_light_poller(
        _sg_id: ServiceGroupId,
        _settings: CmtsOrchestratorSettings,
        cable_modems: list[SgwCableModemModel],
    ) -> list[SgwCableModemModel]:
        return list(cable_modems)

    @staticmethod
    def _default_clock() -> float:
        return float(time.time())

    def _initialize_jitter(self, service_groups: list[ServiceGroupId]) -> None:
        self._jitter_by_sg = {}
        for sg_id in service_groups:
            self._jitter_by_sg[sg_id] = self._resolve_jitter_seconds(sg_id)

    @staticmethod
    def _clamp_jitter(jitter_value: int, max_jitter: int) -> int:
        if jitter_value < JITTER_MIN_SECONDS:
            return JITTER_MIN_SECONDS
        if jitter_value > max_jitter:
            return max_jitter
        return jitter_value


__all__ = [
    "REFRESH_MODE_NONE",
    "REFRESH_MODE_HEAVY",
    "REFRESH_MODE_LIGHT",
    "REFRESH_RESULT_OK",
    "REFRESH_RESULT_ERROR",
    "REFRESH_RESULT_STALE",
    "SgwManager",
]

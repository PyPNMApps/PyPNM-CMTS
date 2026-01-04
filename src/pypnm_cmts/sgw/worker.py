# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Protocol

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.worker_models import (
    InventoryResultModel,
    RefreshLaneStatusModel,
    RefreshState,
    ServingGroupSnapshotModel,
    StateResultModel,
)


class Clock(Protocol):
    """Protocol for a clock abstraction used by SGW workers."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""


class CmtsServingGroupClient(Protocol):
    """Protocol for serving group inventory/state collection."""

    async def fetch_inventory(self, sg_id: ServiceGroupId) -> InventoryResultModel:
        """Collect inventory data for the given service group."""

    async def fetch_state(
        self,
        sg_id: ServiceGroupId,
        inventory: InventoryResultModel,
    ) -> StateResultModel:
        """Collect state data for the given service group."""


class ServingGroupWorker:
    """Worker that maintains a cache snapshot for a single service group."""

    def __init__(
        self,
        sg_id: ServiceGroupId,
        client: CmtsServingGroupClient,
        clock: Clock,
        settings: CmtsOrchestratorSettings,
    ) -> None:
        """
        Initialize a serving group worker with injected dependencies.

        Args:
            sg_id (ServiceGroupId): Service group identifier to manage.
            client (CmtsServingGroupClient): Inventory/state client abstraction.
            clock (Clock): Clock abstraction used for timestamps.
            settings (CmtsOrchestratorSettings): Orchestrator settings containing refresh intervals.
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._sg_id = sg_id
        self._client = client
        self._clock = clock
        self._settings = settings
        self._lock = threading.Lock()
        self._last_inventory: InventoryResultModel | None = None
        self._snapshot = self._build_snapshot(self._clock.now())

    def get_snapshot(self) -> ServingGroupSnapshotModel:
        """
        Return the most recent snapshot without triggering a refresh.

        Returns:
            ServingGroupSnapshotModel: Snapshot payload with age computed from the injected clock.
        """
        now = self._clock.now()
        with self._lock:
            snapshot = self._with_age(self._snapshot, now)
        return snapshot

    async def tick_heavy(self) -> ServingGroupSnapshotModel:
        """
        Execute a heavy refresh cycle to rebuild serving group inventory.

        Returns:
            ServingGroupSnapshotModel: Updated snapshot after the heavy refresh attempt.
        """
        self._set_lane_running(is_heavy=True)
        try:
            inventory = await self._client.fetch_inventory(self._sg_id)
        except Exception as exc:
            return self._set_lane_error(is_heavy=True, message=str(exc))

        now = self._clock.now()
        with self._lock:
            self._last_inventory = inventory
            self._snapshot = self._snapshot.model_copy(
                update={
                    "snapshot_time": now,
                    "modem_count": int(inventory.modem_count),
                }
            )
            self._snapshot = self._set_lane_success_locked(
                is_heavy=True,
                now=now,
            )
        return self._with_age(self._snapshot, now)

    async def tick_light(self) -> ServingGroupSnapshotModel:
        """
        Execute a light refresh cycle to update serving group state.

        Returns:
            ServingGroupSnapshotModel: Updated snapshot after the light refresh attempt.
        """
        self._set_lane_running(is_heavy=False)
        inventory = self._last_inventory
        if inventory is None:
            return self._set_lane_error(is_heavy=False, message="inventory not available for light refresh")

        try:
            await self._client.fetch_state(self._sg_id, inventory)
        except Exception as exc:
            return self._set_lane_error(is_heavy=False, message=str(exc))

        now = self._clock.now()
        with self._lock:
            self._snapshot = self._snapshot.model_copy(update={"snapshot_time": now})
            self._snapshot = self._set_lane_success_locked(
                is_heavy=False,
                now=now,
            )
        return self._with_age(self._snapshot, now)

    def _build_snapshot(self, now: datetime) -> ServingGroupSnapshotModel:
        return ServingGroupSnapshotModel(
            sg_id=self._sg_id,
            snapshot_time=now,
            age_seconds=0.0,
            refresh_state=RefreshState.IDLE,
            heavy_refresh=RefreshLaneStatusModel(),
            light_refresh=RefreshLaneStatusModel(),
            modem_count=0,
        )

    def _set_lane_running(self, is_heavy: bool) -> None:
        now = self._clock.now()
        with self._lock:
            lane = self._snapshot.heavy_refresh if is_heavy else self._snapshot.light_refresh
            lane = lane.model_copy(update={"state": RefreshState.RUNNING, "running": True})
            self._snapshot = self._snapshot.model_copy(
                update={
                    "heavy_refresh": lane if is_heavy else self._snapshot.heavy_refresh,
                    "light_refresh": lane if not is_heavy else self._snapshot.light_refresh,
                    "refresh_state": RefreshState.RUNNING,
                    "snapshot_time": self._snapshot.snapshot_time,
                }
            )
            self._snapshot = self._with_age(self._snapshot, now)

    def _set_lane_error(self, is_heavy: bool, message: str) -> ServingGroupSnapshotModel:
        now = self._clock.now()
        with self._lock:
            lane = self._snapshot.heavy_refresh if is_heavy else self._snapshot.light_refresh
            lane = lane.model_copy(
                update={
                    "state": RefreshState.ERROR,
                    "running": False,
                    "last_error": message,
                }
            )
            self._snapshot = self._snapshot.model_copy(
                update={
                    "heavy_refresh": lane if is_heavy else self._snapshot.heavy_refresh,
                    "light_refresh": lane if not is_heavy else self._snapshot.light_refresh,
                    "refresh_state": RefreshState.ERROR,
                }
            )
            self._snapshot = self._with_age(self._snapshot, now)
            snapshot = self._snapshot
        return snapshot

    def _set_lane_success_locked(self, is_heavy: bool, now: datetime) -> ServingGroupSnapshotModel:
        lane = self._snapshot.heavy_refresh if is_heavy else self._snapshot.light_refresh
        lane = lane.model_copy(
            update={
                "state": RefreshState.IDLE,
                "running": False,
                "last_error": "",
                "last_success_time": now,
            }
        )
        self._snapshot = self._snapshot.model_copy(
            update={
                "heavy_refresh": lane if is_heavy else self._snapshot.heavy_refresh,
                "light_refresh": lane if not is_heavy else self._snapshot.light_refresh,
                "refresh_state": self._resolve_overall_state(
                    heavy=lane if is_heavy else self._snapshot.heavy_refresh,
                    light=lane if not is_heavy else self._snapshot.light_refresh,
                ),
            }
        )
        return self._snapshot

    @staticmethod
    def _resolve_overall_state(
        heavy: RefreshLaneStatusModel,
        light: RefreshLaneStatusModel,
    ) -> RefreshState:
        if heavy.state == RefreshState.ERROR or light.state == RefreshState.ERROR:
            return RefreshState.ERROR
        if heavy.state == RefreshState.RUNNING or light.state == RefreshState.RUNNING:
            return RefreshState.RUNNING
        return RefreshState.IDLE

    def _with_age(self, snapshot: ServingGroupSnapshotModel, now: datetime) -> ServingGroupSnapshotModel:
        age_seconds = max(0.0, (now - snapshot.snapshot_time).total_seconds())
        return snapshot.model_copy(update={"age_seconds": age_seconds})


class ServingGroupWorkerFactory:
    """Factory for constructing serving group workers."""

    @staticmethod
    def build(
        sg_id: ServiceGroupId,
        client: CmtsServingGroupClient,
        clock: Clock,
        settings: CmtsOrchestratorSettings,
    ) -> ServingGroupWorker:
        """
        Build a serving group worker with the required dependencies.

        Args:
            sg_id (ServiceGroupId): Service group identifier to manage.
            client (CmtsServingGroupClient): Inventory/state client abstraction.
            clock (Clock): Clock abstraction used for timestamps.
            settings (CmtsOrchestratorSettings): Orchestrator settings containing refresh intervals.
        """
        return ServingGroupWorker(
            sg_id=sg_id,
            client=client,
            clock=clock,
            settings=settings,
        )


class UtcClock:
    """Clock implementation that returns UTC timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""
        return datetime.now(timezone.utc)


__all__ = [
    "Clock",
    "CmtsServingGroupClient",
    "ServingGroupWorker",
    "ServingGroupWorkerFactory",
    "UtcClock",
]

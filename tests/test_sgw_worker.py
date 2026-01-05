# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.worker import ServingGroupWorker
from pypnm_cmts.sgw.worker_models import (
    InventoryResultModel,
    RefreshState,
    StateResultModel,
)


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=float(seconds))


class FakeCmtsServingGroupClient:
    def __init__(
        self,
        inventory: InventoryResultModel,
        state: StateResultModel,
        fail_inventory: bool = False,
        fail_state: bool = False,
    ) -> None:
        self._inventory = inventory
        self._state = state
        self._fail_inventory = fail_inventory
        self._fail_state = fail_state

    async def fetch_inventory(self, _sg_id: ServiceGroupId) -> InventoryResultModel:
        if self._fail_inventory:
            raise RuntimeError("inventory failure")
        return self._inventory

    async def fetch_state(
        self,
        _sg_id: ServiceGroupId,
        _inventory: InventoryResultModel,
    ) -> StateResultModel:
        if self._fail_state:
            raise RuntimeError("state failure")
        return self._state


def _build_worker(
    clock: FakeClock,
    client: FakeCmtsServingGroupClient,
) -> ServingGroupWorker:
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    return ServingGroupWorker(
        sg_id=ServiceGroupId(1),
        client=client,
        clock=clock,
        settings=settings,
    )


def test_serving_group_worker_cache_first_snapshot() -> None:
    start = datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc)
    clock = FakeClock(start)
    client = FakeCmtsServingGroupClient(
        inventory=InventoryResultModel(modem_count=0),
        state=StateResultModel(updated_count=0),
    )
    worker = _build_worker(clock, client)

    snapshot = worker.get_snapshot()
    assert snapshot.modem_count == 0
    assert snapshot.refresh_state == RefreshState.IDLE
    assert snapshot.age_seconds == 0.0

    clock.advance(5.0)
    snapshot = worker.get_snapshot()
    assert snapshot.age_seconds == 5.0


def test_serving_group_worker_heavy_refresh_success() -> None:
    start = datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc)
    clock = FakeClock(start)
    client = FakeCmtsServingGroupClient(
        inventory=InventoryResultModel(modem_count=7),
        state=StateResultModel(updated_count=0),
    )
    worker = _build_worker(clock, client)

    clock.advance(10.0)
    snapshot = asyncio.run(worker.tick_heavy())

    assert snapshot.modem_count == 7
    assert snapshot.snapshot_time == clock.now()
    assert snapshot.refresh_state == RefreshState.IDLE
    assert snapshot.heavy_refresh.state == RefreshState.IDLE
    assert snapshot.heavy_refresh.last_error == ""


def test_serving_group_worker_light_refresh_success_independent() -> None:
    start = datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc)
    clock = FakeClock(start)
    client = FakeCmtsServingGroupClient(
        inventory=InventoryResultModel(modem_count=3),
        state=StateResultModel(updated_count=2),
    )
    worker = _build_worker(clock, client)

    clock.advance(5.0)
    heavy_snapshot = asyncio.run(worker.tick_heavy())
    heavy_time = heavy_snapshot.heavy_refresh.last_success_time

    clock.advance(5.0)
    light_snapshot = asyncio.run(worker.tick_light())

    assert light_snapshot.light_refresh.state == RefreshState.IDLE
    assert light_snapshot.light_refresh.last_error == ""
    assert light_snapshot.light_refresh.last_success_time == clock.now()
    assert light_snapshot.heavy_refresh.last_success_time == heavy_time


def test_serving_group_worker_heavy_refresh_failure() -> None:
    start = datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc)
    clock = FakeClock(start)
    client = FakeCmtsServingGroupClient(
        inventory=InventoryResultModel(modem_count=0),
        state=StateResultModel(updated_count=0),
        fail_inventory=True,
    )
    worker = _build_worker(clock, client)

    snapshot = asyncio.run(worker.tick_heavy())

    assert snapshot.refresh_state == RefreshState.ERROR
    assert snapshot.heavy_refresh.state == RefreshState.ERROR
    assert snapshot.heavy_refresh.last_error != ""

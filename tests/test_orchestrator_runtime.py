# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import threading
from pathlib import Path

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import CoordinationTickResultModel
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    LeaderId,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.orchestrator.runtime import CmtsOrchestratorRuntime
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


def _build_settings(tmp_path: Path) -> CmtsOrchestratorSettings:
    return CmtsOrchestratorSettings(
        tick_interval_seconds=1,
        leader_ttl_seconds=5,
        lease_ttl_seconds=5,
        state_dir=tmp_path / "coordination",
        adapter={"hostname": "cmts.example", "community": "public"},
        sgw={"discovery": {"mode": "static"}},
    )


def test_runtime_runs_fixed_ticks_without_sleep(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
    )

    service_groups = [ServiceGroupId(1)]
    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=service_groups,
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
    )

    results = runtime.run_forever(max_ticks=3, sleeper=lambda _: None)
    assert len(results) == 3


def test_runtime_stop_prevents_ticks(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
    )

    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[ServiceGroupId(1)],
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
    )

    runtime.stop()
    results = runtime.run_forever(max_ticks=2, sleeper=lambda _: None)
    assert results == []


def test_runtime_release_all_called_on_stop(tmp_path: Path, monkeypatch: object) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
    )

    release_called = {"value": False}

    def _fake_release_all() -> object:
        release_called["value"] = True
        return None

    monkeypatch.setattr(manager, "release_all", _fake_release_all)

    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[ServiceGroupId(1)],
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
    )

    runtime.stop()
    runtime.run_forever(max_ticks=1, sleeper=lambda _: None)
    assert release_called["value"] is True


def test_runtime_runs_in_non_main_thread(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
    )

    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[ServiceGroupId(1)],
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
    )

    results: list[CoordinationTickResultModel] = []
    errors: list[Exception] = []

    def _run() -> None:
        try:
            results.extend(runtime.run_forever(max_ticks=1, sleeper=lambda _: None))
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()

    assert errors == []
    assert len(results) == 1


def test_runtime_writes_and_removes_controller_pidfile(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
        leader_enabled=True,
    )

    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[ServiceGroupId(1)],
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
    )

    pidfile_path = settings.state_dir / "pids" / "controller.pid"
    seen_pidfile = {"value": False}

    def _on_tick(_: CoordinationTickResultModel) -> None:
        if pidfile_path.exists():
            seen_pidfile["value"] = True

    runtime.run_forever(max_ticks=1, sleeper=lambda _: None, on_tick=_on_tick)
    assert seen_pidfile["value"] is True
    assert pidfile_path.exists() is False


def test_runtime_writes_and_removes_worker_pidfile(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
        leader_enabled=False,
    )

    sg_id = ServiceGroupId(7)
    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[sg_id],
        mode=OrchestratorMode.WORKER,
        sg_id=sg_id,
    )

    pidfile_path = settings.state_dir / "pids" / "worker_7.pid"
    seen_pidfile = {"value": False}

    def _on_tick(_: CoordinationTickResultModel) -> None:
        if pidfile_path.exists():
            seen_pidfile["value"] = True

    runtime.run_forever(max_ticks=1, sleeper=lambda _: None, on_tick=_on_tick)
    assert seen_pidfile["value"] is True
    assert pidfile_path.exists() is False

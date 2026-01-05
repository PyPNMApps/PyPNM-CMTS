# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from threading import Event

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.runtime_state import (
    is_sgw_refresh_running,
    reset_sgw_runtime_state,
    set_sgw_startup_success,
    start_sgw_background_refresh,
    stop_sgw_background_refresh,
)
from pypnm_cmts.sgw.store import SgwCacheStore

START_TIMEOUT_SECONDS = 0.5
STOP_TIMEOUT_SECONDS = 0.5
STARTUP_REFRESH_EPOCH = 0.0


def test_sgw_background_refresh_start_stop(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    store = SgwCacheStore()
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    manager = SgwManager(settings=settings, store=store, service_groups=[])
    started = Event()
    stopped = Event()

    def _refresh_forever(*_args: object, **_kwargs: object) -> list[object]:
        started.set()
        stopped.wait(timeout=START_TIMEOUT_SECONDS)
        return []

    def _stop() -> None:
        stopped.set()

    monkeypatch.setattr(manager, "refresh_forever", _refresh_forever)
    monkeypatch.setattr(manager, "stop", _stop)

    set_sgw_startup_success([], store, manager, STARTUP_REFRESH_EPOCH)

    assert start_sgw_background_refresh() is True
    assert started.wait(timeout=START_TIMEOUT_SECONDS)
    assert is_sgw_refresh_running() is True

    stop_sgw_background_refresh(timeout_seconds=STOP_TIMEOUT_SECONDS)
    assert stopped.is_set() is True
    assert is_sgw_refresh_running() is False


def test_sgw_background_refresh_restart_clears_stop(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    store = SgwCacheStore()
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    manager = SgwManager(settings=settings, store=store, service_groups=[])
    started = Event()
    stopped = Event()
    reset_calls = {"count": 0}
    original_reset_stop = manager.reset_stop

    def _refresh_forever(*_args: object, **_kwargs: object) -> list[object]:
        started.set()
        stopped.wait(timeout=START_TIMEOUT_SECONDS)
        return []

    def _stop() -> None:
        stopped.set()

    def _reset_stop() -> None:
        reset_calls["count"] += 1
        original_reset_stop()

    monkeypatch.setattr(manager, "refresh_forever", _refresh_forever)
    monkeypatch.setattr(manager, "stop", _stop)
    monkeypatch.setattr(manager, "reset_stop", _reset_stop)

    set_sgw_startup_success([], store, manager, STARTUP_REFRESH_EPOCH)

    assert start_sgw_background_refresh() is True
    assert started.wait(timeout=START_TIMEOUT_SECONDS)
    assert is_sgw_refresh_running() is True
    stop_sgw_background_refresh(timeout_seconds=STOP_TIMEOUT_SECONDS)
    assert stopped.is_set() is True
    assert is_sgw_refresh_running() is False

    started.clear()
    stopped.clear()
    assert start_sgw_background_refresh() is True
    assert started.wait(timeout=START_TIMEOUT_SECONDS)
    assert is_sgw_refresh_running() is True
    stop_sgw_background_refresh(timeout_seconds=STOP_TIMEOUT_SECONDS)
    assert stopped.is_set() is True
    assert is_sgw_refresh_running() is False
    assert reset_calls["count"] == 2

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.support.web_service_memory_guard import WebServiceMemoryGuard


@pytest.mark.unit
def test_web_service_memory_guard_requests_reload_when_rss_threshold_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.CmtsSystemConfigSettings.web_service_memory_guard_rss_restart_threshold_mb",
        staticmethod(lambda: 1),
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.CmtsSystemConfigSettings.web_service_memory_guard_min_restart_interval_seconds",
        staticmethod(lambda: 0),
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.CmtsSystemConfigSettings.web_service_memory_guard_max_restarts_per_hour",
        staticmethod(lambda: 5),
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.read_process_rss_bytes",
        lambda: 2 * 1024 * 1024,
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.request_web_service_reload",
        lambda reason, actor: calls.append((reason, actor)),
    )

    guard = WebServiceMemoryGuard()

    assert guard.evaluate_once() is True
    assert calls == [("memory_guard_rss_threshold", "cmts.system.webService.memoryGuard")]


@pytest.mark.unit
def test_web_service_memory_guard_skips_reload_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.CmtsSystemConfigSettings.web_service_memory_guard_rss_restart_threshold_mb",
        staticmethod(lambda: 16),
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.CmtsSystemConfigSettings.web_service_memory_guard_min_restart_interval_seconds",
        staticmethod(lambda: 0),
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.CmtsSystemConfigSettings.web_service_memory_guard_max_restarts_per_hour",
        staticmethod(lambda: 5),
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.read_process_rss_bytes",
        lambda: 2 * 1024 * 1024,
    )
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_memory_guard.request_web_service_reload",
        lambda reason, actor: calls.append((reason, actor)),
    )

    guard = WebServiceMemoryGuard()

    assert guard.evaluate_once() is False
    assert calls == []

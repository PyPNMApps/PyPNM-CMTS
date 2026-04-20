# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from pypnm_cmts.config.runtime_flags import ENV_DEBUG_MODE


def _client(monkeypatch: object, debug_mode: bool = False) -> TestClient:
    import pypnm_cmts.api.main as api_main

    if debug_mode:
        monkeypatch.setenv(ENV_DEBUG_MODE, "1")
    else:
        monkeypatch.delenv(ENV_DEBUG_MODE, raising=False)
    importlib.reload(api_main)

    def _noop() -> None:
        return None

    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)
    return TestClient(api_main.app)


def test_debug_routes_are_hidden_and_unreachable_by_default(monkeypatch: object) -> None:
    import pypnm_cmts.api.main as api_main

    try:
        client = _client(monkeypatch, debug_mode=False)
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        assert "/ops/debug/allocateMemory" not in openapi.json()["paths"]
        response = client.post("/ops/debug/allocateMemory", json={"megabytes": 16})
        assert response.status_code == 404
    finally:
        monkeypatch.delenv(ENV_DEBUG_MODE, raising=False)
        importlib.reload(api_main)


def test_debug_routes_are_registered_when_debug_mode_enabled(monkeypatch: object) -> None:
    import pypnm_cmts.api.main as api_main

    try:
        client = _client(monkeypatch, debug_mode=True)
        from pypnm_cmts.api.routes.debug import service as debug_service

        rss_values = iter([256, 768])
        monkeypatch.setattr(debug_service, "read_process_rss_bytes", lambda: next(rss_values))
        monkeypatch.setattr(debug_service, "allocate_retained_debug_memory_mb", lambda megabytes: megabytes * 1024 * 1024)

        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        assert "/ops/debug/allocateMemory" in openapi.json()["paths"]

        response = client.post("/ops/debug/allocateMemory", json={"megabytes": 32})
        assert response.status_code == 200
        payload = response.json()
        assert payload["requested_megabytes"] == 32
        assert payload["rss_before_bytes"] == 256
        assert payload["rss_after_bytes"] == 768
        assert payload["retained_bytes"] == 32 * 1024 * 1024
    finally:
        monkeypatch.delenv(ENV_DEBUG_MODE, raising=False)
        importlib.reload(api_main)

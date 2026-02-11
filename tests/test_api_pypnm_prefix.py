# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from pypnm_cmts.config.runtime_flags import (
    ENV_MUTE_PYPNM_ENDPOINTS,
    ENV_MUTE_TAGS,
    ENV_MUTE_TAGS_HARD,
)


def _client(
    monkeypatch: object,
    mute_pypnm_endpoints: bool = False,
    mute_tags: str = "",
    mute_tags_hard: bool = False,
) -> TestClient:
    import pypnm_cmts.api.main as api_main

    if mute_pypnm_endpoints:
        monkeypatch.setenv(ENV_MUTE_PYPNM_ENDPOINTS, "1")
    else:
        monkeypatch.delenv(ENV_MUTE_PYPNM_ENDPOINTS, raising=False)
    if mute_tags.strip() != "":
        monkeypatch.setenv(ENV_MUTE_TAGS, mute_tags)
    else:
        monkeypatch.delenv(ENV_MUTE_TAGS, raising=False)
    if mute_tags_hard:
        monkeypatch.setenv(ENV_MUTE_TAGS_HARD, "1")
    else:
        monkeypatch.delenv(ENV_MUTE_TAGS_HARD, raising=False)
    importlib.reload(api_main)

    def _noop() -> None:
        return None

    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)
    return TestClient(api_main.app)


def test_pypnm_routes_are_mounted_under_cm(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.get("/cm/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] != ""


def test_pypnm_routes_are_not_mounted_under_pypnm(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.get("/pypnm/health")
    assert response.status_code == 404


def test_pypnm_routes_can_be_muted_from_startup_env(monkeypatch: object) -> None:
    import pypnm_cmts.api.main as api_main

    try:
        client = _client(monkeypatch, mute_pypnm_endpoints=True)
        response = client.get("/cm/health")
        assert response.status_code == 404
    finally:
        monkeypatch.delenv(ENV_MUTE_PYPNM_ENDPOINTS, raising=False)
        monkeypatch.delenv(ENV_MUTE_TAGS, raising=False)
        monkeypatch.delenv(ENV_MUTE_TAGS_HARD, raising=False)
        importlib.reload(api_main)


def test_muted_tags_hide_routes_from_openapi(monkeypatch: object) -> None:
    import pypnm_cmts.api.main as api_main

    try:
        client = _client(monkeypatch, mute_tags="Operational")
        response = client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert "/ops/health" not in paths
        assert "/cmts/system/sysDescr" in paths
    finally:
        monkeypatch.delenv(ENV_MUTE_TAGS, raising=False)
        monkeypatch.delenv(ENV_MUTE_TAGS_HARD, raising=False)
        importlib.reload(api_main)


def test_muted_tags_hard_mode_returns_forbidden(monkeypatch: object) -> None:
    import pypnm_cmts.api.main as api_main

    try:
        client = _client(
            monkeypatch,
            mute_tags="Operational",
            mute_tags_hard=True,
        )
        response = client.get("/ops/health")
        assert response.status_code == 403
        assert response.json()["detail"] == "Endpoint disabled by policy"
        assert response.headers["X-Endpoint-Policy"] == "muted-tag"
    finally:
        monkeypatch.delenv(ENV_MUTE_TAGS, raising=False)
        monkeypatch.delenv(ENV_MUTE_TAGS_HARD, raising=False)
        importlib.reload(api_main)

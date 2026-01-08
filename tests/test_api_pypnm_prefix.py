# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from fastapi.testclient import TestClient

from pypnm_cmts.api.main import app


def _client(monkeypatch: object) -> TestClient:
    def _noop() -> None:
        return None

    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)
    return TestClient(app)


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

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


def test_modulation_profile_status_route_is_mounted(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.post("/cmts/pnm/sg/ds/ofdm/modulationProfile/status", json={})
    assert response.status_code == 422


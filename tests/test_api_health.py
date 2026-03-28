# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from pypnm_cmts.api.health import HealthDataInfo, HealthMemoryInfo


def _client(monkeypatch: object) -> TestClient:
    import pypnm_cmts.api.main as api_main

    importlib.reload(api_main)

    def _noop() -> None:
        return None

    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)
    return TestClient(api_main.app)


def test_health_returns_http_200_with_expected_shape(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] in {"ok", "warning", "error", "unknown"}
    assert "message" in payload
    assert payload["service"]["name"] == "pypnm-docsis-cmts"
    assert isinstance(payload["service"].get("version"), str)
    assert "uptime" in payload
    assert "memory" in payload
    assert "data" in payload
    assert payload["version"] == payload["service"]["version"]


def test_health_service_name_is_cmts_identity(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"]["name"] == "pypnm-docsis-cmts"


def test_health_status_is_allowed_enum_value(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "warning", "error", "unknown"}


def test_health_handles_missing_memory_stats_without_crashing(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    monkeypatch.setattr(
        "pypnm_cmts.api.main._health_service._collect_memory_info",
        lambda: HealthMemoryInfo(),
    )

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"]["name"] == "pypnm-docsis-cmts"
    assert payload["memory"]["rss_bytes"] is None
    assert payload["memory"]["total_bytes"] is None
    assert payload["status"] == "warning"


def test_health_handles_missing_data_path_stats_without_crashing(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    monkeypatch.setattr(
        "pypnm_cmts.api.main._health_service._collect_data_info",
        lambda: HealthDataInfo(path=None, size_bytes=None, directories=None),
    )

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"]["name"] == "pypnm-docsis-cmts"
    assert payload["data"]["path"] is None
    assert payload["data"]["size_bytes"] is None
    assert payload["data"]["directories"] is None
    assert payload["status"] == "warning"


def test_health_openapi_schema_matches_required_contract(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    document = response.json()
    schema_ref = document["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    health_schema_name = schema_ref.rsplit("/", maxsplit=1)[-1]
    health_schema = document["components"]["schemas"][health_schema_name]
    service_schema_name = health_schema["properties"]["service"]["$ref"].rsplit("/", maxsplit=1)[-1]
    service_schema = document["components"]["schemas"][service_schema_name]

    assert health_schema["required"] == ["status", "service"]
    assert health_schema["properties"]["status"]["enum"] == ["ok", "warning", "error", "unknown"]
    assert service_schema["required"] == ["name"]
    assert service_schema["properties"]["name"]["const"] == "pypnm-docsis-cmts"

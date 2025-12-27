# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import httpx  # noqa: F401
    HAS_HTTPX = True
except ModuleNotFoundError:
    HAS_HTTPX = False

if HAS_HTTPX:
    from fastapi.testclient import TestClient

SUCCESS_STATUS_CODE = 200
VALIDATION_STATUS_CODE = 422


def _write_system_config(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_pypnm_system_config(path: Path, log_dir: Path) -> None:
    payload = {
        "logging": {
            "log_dir": str(log_dir),
            "log_filename": "pypnm.log",
            "log_level": "INFO",
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _load_app(tmp_path: Path) -> object:
    from pypnm.config.config_manager import ConfigManager
    from pypnm.config.system_config_settings import SystemConfigSettings

    config_path = tmp_path / "pypnm_system.json"
    log_dir = tmp_path / "pypnm_logs"
    _write_pypnm_system_config(config_path, log_dir)
    SystemConfigSettings._cfg = ConfigManager(config_path=str(config_path))

    from pypnm_cmts.api.main import app

    return app


def test_httpx_dependency_available() -> None:
    if not HAS_HTTPX:
        pytest.xfail("httpx not installed; API tests are skipped.")


def test_health_returns_version(tmp_path: Path) -> None:
    if not HAS_HTTPX:
        pytest.skip("httpx not installed.")
    app = _load_app(tmp_path)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == SUCCESS_STATUS_CODE
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload


def test_orchestrator_run_standalone_returns_payload(tmp_path: Path) -> None:
    if not HAS_HTTPX:
        pytest.skip("httpx not installed.")
    app = _load_app(tmp_path)
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    client = TestClient(app)
    response = client.post(
        "/orchestrator/run",
        json={
            "mode": "standalone",
            "config_path": str(config_path),
            "state_dir": str(state_dir),
        },
    )
    assert response.status_code == SUCCESS_STATUS_CODE
    payload = response.json()
    assert "mode" in payload
    assert "inventory" in payload
    assert "coordination_tick" in payload
    assert "coordination_status" in payload
    assert "leader_status" in payload
    assert "work_results" in payload
    assert "tick_index" in payload
    assert "run_id" in payload
    assert "lease_held" in payload


def test_orchestrator_run_worker_requires_sg_id(tmp_path: Path) -> None:
    if not HAS_HTTPX:
        pytest.skip("httpx not installed.")
    app = _load_app(tmp_path)
    client = TestClient(app)
    response = client.post(
        "/orchestrator/run",
        json={"mode": "worker"},
    )
    assert response.status_code == VALIDATION_STATUS_CODE
    assert "sg_id is required" in response.text


def test_orchestrator_status_does_not_persist_results(tmp_path: Path) -> None:
    if not HAS_HTTPX:
        pytest.skip("httpx not installed.")
    app = _load_app(tmp_path)
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    client = TestClient(app)
    response = client.post(
        "/orchestrator/status",
        json={
            "mode": "standalone",
            "config_path": str(config_path),
            "state_dir": str(state_dir),
        },
    )
    assert response.status_code == SUCCESS_STATUS_CODE
    payload = response.json()
    assert "inventory" in payload
    assert "coordination_status" in payload
    assert "leader_status" in payload
    assert "target_service_groups" in payload

    results_root = state_dir / "results"
    if results_root.exists():
        assert list(results_root.glob("sg_*")) == []
        assert list(results_root.rglob("*.json")) == []

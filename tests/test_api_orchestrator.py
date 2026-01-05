# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import ValidationError


def _write_system_config(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "adapter": {
                "hostname": "cmts.example",
                "community": "public",
                "write_community": "",
                "port": 161,
            },
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
            "sgw": {"discovery": {"mode": "static"}},
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _load_app(tmp_path: Path) -> FastAPI:
    from pypnm_cmts.api.routes.orchestrator.router import router as orchestrator_router
    from pypnm_cmts.version import __version__

    app = FastAPI(title="PyPNM-CMTS Test API", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(orchestrator_router)
    return app


def _call_route(app: FastAPI, path: str, method: str, payload: object | None = None) -> object:
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path != path:
            continue
        if method.upper() not in route.methods:
            continue
        if payload is None:
            return route.endpoint()
        return route.endpoint(payload)
    raise AssertionError(f"Route not found: {method} {path}")


def test_health_returns_version(tmp_path: Path) -> None:
    app = _load_app(tmp_path)
    payload = _call_route(app, "/health", "GET")
    assert isinstance(payload, dict)
    assert payload.get("status") == "ok"
    assert payload["status"] == "ok"
    assert "version" in payload


def test_orchestrator_run_standalone_returns_payload(tmp_path: Path) -> None:
    app = _load_app(tmp_path)
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)
    request_payload = {
        "mode": "standalone",
        "config_path": str(config_path),
        "state_dir": str(state_dir),
    }
    from pypnm_cmts.api.routes.orchestrator.schemas import OrchestratorRunRequest

    request = OrchestratorRunRequest.model_validate(request_payload)
    payload = _call_route(app, "/orchestrator/run", "POST", request)
    assert hasattr(payload, "mode")
    assert hasattr(payload, "inventory")
    assert hasattr(payload, "coordination_tick")
    assert hasattr(payload, "coordination_status")
    assert hasattr(payload, "leader_status")
    assert hasattr(payload, "work_results")
    assert hasattr(payload, "tick_index")
    assert hasattr(payload, "run_id")
    assert hasattr(payload, "lease_held")


def test_orchestrator_run_worker_requires_sg_id(tmp_path: Path) -> None:
    _load_app(tmp_path)
    from pypnm_cmts.api.routes.orchestrator.schemas import OrchestratorRunRequest

    with pytest.raises(ValidationError) as exc_info:
        OrchestratorRunRequest.model_validate({"mode": "worker"})
    assert "sg_id is required" in str(exc_info.value)


def test_orchestrator_status_does_not_persist_results(tmp_path: Path) -> None:
    app = _load_app(tmp_path)
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)
    request_payload = {
        "mode": "standalone",
        "config_path": str(config_path),
        "state_dir": str(state_dir),
    }
    from pypnm_cmts.api.routes.orchestrator.schemas import OrchestratorRunRequest

    request = OrchestratorRunRequest.model_validate(request_payload)
    payload = _call_route(app, "/orchestrator/status", "POST", request)
    assert hasattr(payload, "inventory")
    assert hasattr(payload, "coordination_status")
    assert hasattr(payload, "leader_status")
    assert hasattr(payload, "target_service_groups")

    results_root = state_dir / "results"
    if results_root.exists():
        assert list(results_root.glob("sg_*")) == []
        assert list(results_root.rglob("*.json")) == []

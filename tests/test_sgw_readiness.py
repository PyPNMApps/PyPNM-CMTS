# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.runtime_state import (
    reset_sgw_runtime_state,
    set_sgw_startup_success,
)
from pypnm_cmts.sgw.store import SgwCacheStore
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__


def _load_app(settings: CmtsOrchestratorSettings, monkeypatch: object) -> FastAPI:
    from pypnm_cmts.api.routes.operational.router import router as operational_router

    app = FastAPI(title="PyPNM-CMTS Operational API", version=__version__)
    app.include_router(operational_router)

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls, **_kwargs: settings),
    )
    return app


def _build_settings(state_dir: Path) -> CmtsOrchestratorSettings:
    payload = {
        "mode": OrchestratorMode.STANDALONE,
        "state_dir": str(state_dir),
        "adapter": {"hostname": "cmts.example", "community": "public"},
    }
    return CmtsOrchestratorSettings.model_validate(payload)


def test_ops_ready_returns_sgw_startup_when_pending(tmp_path: Path, monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")
    app = _load_app(settings, monkeypatch)

    with TestClient(app) as client:
        response = client.get("/ops/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == OperationalStatus.ERROR.value
        assert payload["failed_check"] == ReadinessCheck.SGW_STARTUP.value


def test_ops_ready_returns_sgw_cache_when_missing_entries(tmp_path: Path, monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")
    sg_ids = [ServiceGroupId(1)]
    last_refresh_epoch = 1000.0
    store = SgwCacheStore()
    manager = SgwManager(settings=settings, store=store, service_groups=sg_ids)
    set_sgw_startup_success(sg_ids, store, manager, last_refresh_epoch)

    app = _load_app(settings, monkeypatch)
    with TestClient(app) as client:
        response = client.get("/ops/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["failed_check"] == ReadinessCheck.SGW_CACHE.value

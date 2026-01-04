# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypnm.lib.types import HostNameStr

from pypnm_cmts.api.main import app
from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import SgwCableModemModel, SgwSnapshotPayloadModel
from pypnm_cmts.sgw.runtime_state import (
    get_sgw_manager,
    get_sgw_startup_status,
    get_sgw_store,
    reset_sgw_runtime_state,
)
from pypnm_cmts.sgw.startup import SgwStartupService


def _build_settings(state_dir: Path) -> CmtsOrchestratorSettings:
    payload = {
        "adapter": {
            "hostname": "cmts.example",
            "community": "public",
            "write_community": "",
            "port": 161,
        },
        "state_dir": str(state_dir),
    }
    return CmtsOrchestratorSettings.model_validate(payload)


def _build_discovery_result(sg_ids: list[ServiceGroupId]) -> InventoryDiscoveryResultModel:
    return InventoryDiscoveryResultModel(
        cmts_host=HostNameStr("cmts.example"),
        discovered_sg_ids=sg_ids,
        per_sg=[],
    )


def _patch_pollers(monkeypatch: object) -> None:
    def _fake_heavy(_sg_id: ServiceGroupId, _settings: CmtsOrchestratorSettings) -> SgwSnapshotPayloadModel:
        return SgwSnapshotPayloadModel()

    def _fake_light(
        _sg_id: ServiceGroupId,
        _settings: CmtsOrchestratorSettings,
        cable_modems: list[SgwCableModemModel],
    ) -> list[SgwCableModemModel]:
        return list(cable_modems)

    monkeypatch.setattr("pypnm_cmts.sgw.startup.sgw_heavy_poller", _fake_heavy)
    monkeypatch.setattr("pypnm_cmts.sgw.startup.sgw_light_poller", _fake_light)


def test_startup_discovers_sgs_and_primes_cache(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")
    sg_ids = [ServiceGroupId(1), ServiceGroupId(2), ServiceGroupId(3)]

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)
    async def _fake_discover(self: object, state_dir: Path | None = None) -> InventoryDiscoveryResultModel:
        _ = state_dir
        return _build_discovery_result(sg_ids)

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_inventory",
        _fake_discover,
    )
    monkeypatch.setattr(
        "pypnm_cmts.sgw.startup.SgwStartupService._now_epoch",
        staticmethod(lambda: 1234.0),
    )

    with TestClient(app):
        status = get_sgw_startup_status()
        assert status.discovery_ok is True
        assert status.discovered_sg_ids == sg_ids
        store = get_sgw_store()
        assert store is not None
        for sg_id in sg_ids:
            entry = store.get_entry(sg_id)
            assert entry is not None
            assert float(entry.snapshot.metadata.snapshot_time_epoch) > 0.0


def test_readiness_true_when_discovery_succeeds(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")
    sg_ids = [ServiceGroupId(1), ServiceGroupId(2)]

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)
    async def _fake_discover(self: object, state_dir: Path | None = None) -> InventoryDiscoveryResultModel:
        _ = state_dir
        return _build_discovery_result(sg_ids)

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_inventory",
        _fake_discover,
    )
    monkeypatch.setattr(
        "pypnm_cmts.sgw.startup.SgwStartupService._now_epoch",
        staticmethod(lambda: 4321.0),
    )

    with TestClient(app) as client:
        response = client.get("/ops/ready")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == OperationalStatus.OK.value
        assert payload["discovery_ok"] is True
        assert payload["sgw_ready"] is True
        assert payload["discovered_sg_ids"] == [1, 2]


def test_readiness_false_when_discovery_fails(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)

    async def _raise_discovery(self: object, state_dir: Path | None = None) -> InventoryDiscoveryResultModel:
        _ = state_dir
        raise RuntimeError("discovery failed")

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_inventory",
        _raise_discovery,
    )

    with TestClient(app) as client:
        response = client.get("/ops/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["failed_check"] == ReadinessCheck.SGW_DISCOVERY.value
        assert payload["message"] != ""

    status = get_sgw_startup_status()
    assert status.startup_completed is True
    assert status.discovery_ok is False
    assert status.prime_failed is False
    assert status.error_message != ""


def test_startup_disabled_mode_uses_coherent_store_and_manager(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    now_epoch = 1234.0
    settings = CmtsOrchestratorSettings.model_validate({"sgw": {"enabled": False}})

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)
    monkeypatch.setattr(
        "pypnm_cmts.sgw.startup.SgwStartupService._now_epoch",
        staticmethod(lambda: now_epoch),
    )

    asyncio.run(SgwStartupService().initialize())

    store = get_sgw_store()
    manager = get_sgw_manager()
    assert store is not None
    assert manager is not None
    assert manager.get_store() is store


def test_startup_prime_failure_records_failure(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")
    sg_ids = [ServiceGroupId(1)]
    error_message = "prime failed"

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)
    async def _fake_discover(self: object, state_dir: Path | None = None) -> InventoryDiscoveryResultModel:
        _ = state_dir
        return _build_discovery_result(sg_ids)

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_inventory",
        _fake_discover,
    )

    def _raise_refresh(self: SgwManager, _now_epoch: float) -> None:
        raise RuntimeError(error_message)

    monkeypatch.setattr(SgwManager, "refresh_once", _raise_refresh)

    with TestClient(app) as client:
        response = client.get("/ops/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["failed_check"] == ReadinessCheck.SGW_PRIME.value
        assert error_message in payload["message"]
        assert payload["discovered_sg_ids"] == [1]

    status = get_sgw_startup_status()
    assert status.startup_completed is True
    assert status.discovery_ok is True
    assert status.prime_failed is True
    assert status.discovered_sg_ids == sg_ids
    assert error_message in status.error_message


@pytest.mark.unit
def test_startup_starts_background_refresh(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    settings = _build_settings(tmp_path / "coordination")
    sg_ids = [ServiceGroupId(1)]
    start_calls = {"count": 0}

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)

    async def _fake_discover(self: object, state_dir: Path | None = None) -> InventoryDiscoveryResultModel:
        _ = state_dir
        return _build_discovery_result(sg_ids)

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_inventory",
        _fake_discover,
    )
    monkeypatch.setattr(
        "pypnm_cmts.sgw.startup.SgwStartupService._now_epoch",
        staticmethod(lambda: 1234.0),
    )
    monkeypatch.setattr(
        "pypnm_cmts.sgw.startup.SgwStartupService._pytest_running",
        staticmethod(lambda: False),
    )

    def _start_refresh() -> bool:
        start_calls["count"] += 1
        return True

    monkeypatch.setattr("pypnm_cmts.sgw.startup.start_sgw_background_refresh", _start_refresh)

    asyncio.run(SgwStartupService().initialize())

    assert start_calls["count"] == 1

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypnm.lib.inet import InetAddressStr
from pypnm.lib.types import HostNameStr

from pypnm_cmts.api.main import app
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.discovery import ServiceGroupDiscovery
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import SgwCableModemModel, SgwSnapshotPayloadModel
from pypnm_cmts.sgw.precheck import CmtsStartupPrecheckResult
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
        "sgw": {"discovery": {"mode": "static"}},
        "state_dir": str(state_dir),
    }
    return CmtsOrchestratorSettings.model_validate(payload)


class FakeDiscovery:
    """Test discovery provider for deterministic SG results."""

    def __init__(self, sg_ids: list[ServiceGroupId], error: Exception | None = None) -> None:
        self._sg_ids = list(sg_ids)
        self._error = error

    def discover(self, _settings: CmtsOrchestratorSettings) -> list[ServiceGroupId]:
        if self._error is not None:
            raise self._error
        return list(self._sg_ids)


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


def _set_discovery(monkeypatch: object, discovery: ServiceGroupDiscovery) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.api.main._sgw_startup_service",
        SgwStartupService(discovery=discovery),
    )


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
    _set_discovery(monkeypatch, FakeDiscovery(sg_ids))
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
    _set_discovery(monkeypatch, FakeDiscovery(sg_ids))
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

    _set_discovery(monkeypatch, FakeDiscovery([], error=RuntimeError("discovery failed")))

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

    asyncio.run(SgwStartupService(discovery=FakeDiscovery([])).initialize())

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
    _set_discovery(monkeypatch, FakeDiscovery(sg_ids))

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
    _set_discovery(monkeypatch, FakeDiscovery(sg_ids))
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

    asyncio.run(SgwStartupService(discovery=FakeDiscovery(sg_ids)).initialize())

    assert start_calls["count"] == 1


def test_startup_snmp_mode_uses_threaded_discovery(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    payload = {
        "adapter": {
            "hostname": "cmts.example",
            "community": "public",
            "write_community": "",
            "port": 161,
        },
        "state_dir": str(tmp_path / "coordination"),
        "sgw": {"discovery": {"mode": "snmp"}},
    }
    settings = CmtsOrchestratorSettings.model_validate(payload)

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)

    async def _fake_precheck(self: object, _settings: CmtsOrchestratorSettings) -> CmtsStartupPrecheckResult:
        return CmtsStartupPrecheckResult(
            ping_ok=True,
            snmp_ok=True,
            hostname=HostNameStr("cmts.example"),
            inet=InetAddressStr("192.168.0.100"),
        )

    monkeypatch.setattr("pypnm_cmts.sgw.startup.CmtsStartupPrecheck.run", _fake_precheck)

    async def _fake_discover_service_groups(self: object) -> list[CmtsServiceGroupModel]:
        return [
            CmtsServiceGroupModel(md_cm_sg_id=3),
            CmtsServiceGroupModel(md_cm_sg_id=1),
            CmtsServiceGroupModel(md_cm_sg_id=3),
        ]

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_service_groups",
        _fake_discover_service_groups,
    )
    monkeypatch.setattr(
        "pypnm_cmts.sgw.startup.SgwStartupService._now_epoch",
        staticmethod(lambda: 1234.0),
    )

    asyncio.run(SgwStartupService().initialize())

    status = get_sgw_startup_status()
    assert status.discovery_ok is True
    assert status.discovered_sg_ids == [ServiceGroupId(1), ServiceGroupId(3)]


@pytest.mark.unit
def test_startup_snmp_mode_precheck_failure(monkeypatch: object, tmp_path: Path) -> None:
    reset_sgw_runtime_state()
    payload = {
        "adapter": {
            "hostname": "cmts.example",
            "community": "public",
            "write_community": "",
            "port": 161,
        },
        "state_dir": str(tmp_path / "coordination"),
        "sgw": {"discovery": {"mode": "snmp"}},
    }
    settings = CmtsOrchestratorSettings.model_validate(payload)

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls: settings),
    )
    _patch_pollers(monkeypatch)

    async def _fake_precheck(self: object, _settings: CmtsOrchestratorSettings) -> CmtsStartupPrecheckResult:
        return CmtsStartupPrecheckResult(
            ping_ok=False,
            snmp_ok=False,
            hostname=HostNameStr("cmts.example"),
            inet=InetAddressStr("192.168.0.100"),
            error_message="cmts ping check failed",
        )

    monkeypatch.setattr("pypnm_cmts.sgw.startup.CmtsStartupPrecheck.run", _fake_precheck)

    asyncio.run(SgwStartupService().initialize())

    status = get_sgw_startup_status()
    assert status.startup_completed is True
    assert status.discovery_ok is False
    assert status.error_message == "cmts ping check failed"

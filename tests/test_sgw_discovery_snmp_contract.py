# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

import pypnm_cmts.sgw.discovery as discovery_module
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.discovery import SnmpServiceGroupDiscovery


def _settings_payload() -> dict[str, object]:
    return {
        "adapter": {
            "hostname": "cmts.example",
            "community": "public",
            "write_community": "private",
            "port": 161,
        }
    }


@pytest.mark.unit
def test_snmp_discovery_dedupes_and_sorts(monkeypatch: pytest.MonkeyPatch) -> None:
    discovery = SnmpServiceGroupDiscovery()
    settings = CmtsOrchestratorSettings.model_validate(_settings_payload())

    def _fake_discover(
        _self: SnmpServiceGroupDiscovery,
        _settings: CmtsOrchestratorSettings,
    ) -> list[CmtsServiceGroupModel]:
        return [
            CmtsServiceGroupModel(md_cm_sg_id=3),
            CmtsServiceGroupModel(md_cm_sg_id=1),
            CmtsServiceGroupModel(md_cm_sg_id=3),
        ]

    monkeypatch.setattr(SnmpServiceGroupDiscovery, "_discover_service_groups", _fake_discover)

    result = discovery.discover(settings)

    assert [int(sg_id) for sg_id in result] == [1, 3]


@pytest.mark.unit
def test_snmp_discovery_empty_result_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    discovery = SnmpServiceGroupDiscovery()
    settings = CmtsOrchestratorSettings.model_validate(_settings_payload())

    def _fake_discover(
        _self: SnmpServiceGroupDiscovery,
        _settings: CmtsOrchestratorSettings,
    ) -> list[CmtsServiceGroupModel]:
        return []

    monkeypatch.setattr(SnmpServiceGroupDiscovery, "_discover_service_groups", _fake_discover)

    result = discovery.discover(settings)

    assert result == []


@pytest.mark.unit
def test_snmp_discovery_failure_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    discovery = SnmpServiceGroupDiscovery()
    settings = CmtsOrchestratorSettings.model_validate(_settings_payload())

    def _raise_error(_coro: object) -> list[CmtsServiceGroupModel]:
        close_fn = getattr(_coro, "close", None)
        if close_fn is not None:
            close_fn()
        raise RuntimeError("boom")

    monkeypatch.setattr(discovery_module, "_run_asyncio", _raise_error)

    with pytest.raises(RuntimeError, match="SNMP discovery failed: boom"):
        discovery._discover_service_groups(settings)


@pytest.mark.unit
def test_snmp_discovery_requires_hostname_and_community() -> None:
    discovery = SnmpServiceGroupDiscovery()
    settings = CmtsOrchestratorSettings.model_validate(_settings_payload())

    settings = settings.model_copy(update={"adapter": settings.adapter.model_copy(update={"hostname": ""})})
    with pytest.raises(ValueError, match="adapter.hostname must be set for snmp discovery"):
        discovery.discover(settings)

    settings = CmtsOrchestratorSettings.model_validate(_settings_payload())
    settings = settings.model_copy(update={"adapter": settings.adapter.model_copy(update={"community": ""})})
    with pytest.raises(ValueError, match="adapter.community must be set for snmp discovery"):
        discovery.discover(settings)


@pytest.mark.unit
def test_snmp_discovery_returns_service_group_ids() -> None:
    discovery = SnmpServiceGroupDiscovery()
    settings = CmtsOrchestratorSettings.model_validate(_settings_payload())

    def _fake_discover(_settings: CmtsOrchestratorSettings) -> list[CmtsServiceGroupModel]:
        return [CmtsServiceGroupModel(md_cm_sg_id=7)]

    discovery._discover_service_groups = _fake_discover

    result = discovery.discover(settings)

    assert result == [ServiceGroupId(7)]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.discovery import StaticServiceGroupDiscovery


@pytest.mark.unit
def test_static_discovery_dedupes_and_sorts_enabled() -> None:
    payload = {
        "sgw": {"discovery": {"mode": "static"}},
        "service_groups": [
            {"sg_id": 2, "enabled": True, "name": "sg-2"},
            {"sg_id": 1, "enabled": True, "name": "sg-1"},
            {"sg_id": 2, "enabled": True, "name": "sg-2-dup"},
            {"sg_id": 3, "enabled": False, "name": "sg-3"},
        ]
    }
    settings = CmtsOrchestratorSettings.model_validate(payload)

    result = StaticServiceGroupDiscovery().discover(settings)

    assert result == [ServiceGroupId(1), ServiceGroupId(2)]


@pytest.mark.unit
def test_static_discovery_empty_config_returns_empty_list() -> None:
    settings = CmtsOrchestratorSettings.model_validate({"sgw": {"discovery": {"mode": "static"}}})

    result = StaticServiceGroupDiscovery().discover(settings)

    assert result == []


@pytest.mark.unit
def test_static_discovery_invalid_sg_id_raises() -> None:
    payload = {
        "sgw": {"discovery": {"mode": "static"}},
        "service_groups": [{"sg_id": 0, "enabled": True, "name": "bad"}],
    }

    with pytest.raises(ValueError):
        CmtsOrchestratorSettings.model_validate(payload)

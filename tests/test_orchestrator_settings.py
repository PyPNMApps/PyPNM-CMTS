# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings


@pytest.mark.unit
def test_from_system_config_uses_cmts_adapter_defaults(tmp_path: Path) -> None:
    payload = {
        "pypnm-cmts": {
            "cmts": [
                {
                    "device": {
                        "hostname": "cmts.example",
                    },
                    "SNMP": {
                        "version": {
                            "2c": {
                                "read_community": "public",
                                "write_community": "private",
                                "port": 161,
                            }
                        }
                    },
                }
            ]
        }
    }
    config_path = tmp_path / "system.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    settings = CmtsOrchestratorSettings.from_system_config(config_path=str(config_path))

    assert str(settings.adapter.hostname) == "cmts.example"
    assert str(settings.adapter.community) == "public"
    assert str(settings.adapter.write_community) == "private"
    assert int(settings.adapter.port) == 161

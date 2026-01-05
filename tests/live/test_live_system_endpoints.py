# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.main import app
from pypnm_cmts.api.routes.system.schemas import CmtsSysDescrResponse
from pypnm_cmts.config.orchestrator_config import (
    ENV_ADAPTER_HOSTNAME,
    ENV_ADAPTER_READ_COMMUNITY,
)

ENV_LIVE_HOSTNAME = "PYPNM_CMTS_LIVE_HOSTNAME"
ENV_LIVE_COMMUNITY = "PYPNM_CMTS_LIVE_SNMP_COMMUNITY"
ENV_LIVE_PORT = "PYPNM_CMTS_LIVE_SNMP_PORT"
DEFAULT_SNMP_PORT = 161


async def _noop() -> None:
    return


def _disable_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)


def _live_hostname() -> str:
    return str(os.environ.get(ENV_LIVE_HOSTNAME, "")).strip()


def _live_community() -> str:
    return str(os.environ.get(ENV_LIVE_COMMUNITY, "")).strip()


def _live_port() -> int:
    port_value = str(os.environ.get(ENV_LIVE_PORT, "")).strip()
    if port_value == "":
        return DEFAULT_SNMP_PORT
    return int(port_value)


@pytest.mark.live_cmts
def test_live_system_sysdescr(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_startup(monkeypatch)
    hostname = _live_hostname()
    community = _live_community()
    monkeypatch.setenv(ENV_ADAPTER_HOSTNAME, hostname)
    monkeypatch.setenv(ENV_ADAPTER_READ_COMMUNITY, community)

    with TestClient(app) as client:
        response = client.get("/cmts/system/sysDescr")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["hostname"] == hostname
        response_model = CmtsSysDescrResponse.model_validate(payload)
        assert response_model.results.is_empty is False

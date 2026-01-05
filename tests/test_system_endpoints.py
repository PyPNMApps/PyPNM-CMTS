# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import HostNameStr, InetAddressStr

from pypnm_cmts.api.main import app
from pypnm_cmts.api.routes.system.schemas import (
    CmtsSysDescrRequest,
    CmtsSysDescrResponse,
)
from pypnm_cmts.config.orchestrator_config import (
    ENV_ADAPTER_HOSTNAME,
    ENV_ADAPTER_READ_COMMUNITY,
)
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


async def _noop() -> None:
    return


def _disable_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)


@pytest.mark.unit
def test_system_sysdescr_accepts_runtime_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_startup(monkeypatch)
    monkeypatch.setenv(ENV_ADAPTER_HOSTNAME, "192.168.0.100")
    monkeypatch.setenv(ENV_ADAPTER_READ_COMMUNITY, "public")

    async def _fake_sysdescr(request: object) -> CmtsSysDescrResponse:
        assert isinstance(request, CmtsSysDescrRequest)
        request_hostname = request.target.hostname
        request_community = request.snmp.snmp_v2c.community
        assert request_hostname == "192.168.0.100"
        assert request_community == "public"
        return CmtsSysDescrResponse(
            hostname=HostNameStr("192.168.0.100"),
            ip_address=InetAddressStr("192.168.0.100"),
            status=ServiceStatusCode.SUCCESS,
            message="",
            results=CmtsSysDescrModel.empty(),
        )

    monkeypatch.setattr("pypnm_cmts.api.routes.system.service.SystemCmtsSnmpService.get_sysdescr", _fake_sysdescr)

    with TestClient(app) as client:
        response = client.get("/cmts/system/sysDescr")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["hostname"] == "192.168.0.100"


@pytest.mark.unit
def test_system_sysdescr_accepts_empty_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_startup(monkeypatch)

    async def _fake_sysdescr(_request: object) -> CmtsSysDescrResponse:
        return CmtsSysDescrResponse(
            hostname=HostNameStr("192.168.0.100"),
            ip_address=InetAddressStr("192.168.0.100"),
            status=ServiceStatusCode.SUCCESS,
            message="",
            results=CmtsSysDescrModel.empty(),
        )

    monkeypatch.setattr("pypnm_cmts.api.routes.system.service.SystemCmtsSnmpService.get_sysdescr", _fake_sysdescr)

    with TestClient(app) as client:
        response = client.get("/cmts/system/sysDescr")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["hostname"] == "192.168.0.100"

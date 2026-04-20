# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pathlib import Path

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
from pypnm_cmts.config.runtime_flags import ENV_WEB_SERVICE_RELOAD_SENTINEL
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


async def _noop() -> None:
    return


def _disable_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)


def _patch_system_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        CmtsSystemConfigSettings,
        "cmts_device_hostname",
        staticmethod(lambda _idx=0: "192.168.0.100"),
    )
    monkeypatch.setattr(
        CmtsSystemConfigSettings,
        "cmts_snmp_v2c_read_community",
        staticmethod(lambda _idx=0: "public"),
    )
    monkeypatch.setattr(
        CmtsSystemConfigSettings,
        "cmts_snmp_v2c_port",
        staticmethod(lambda _idx=0: 161),
    )


@pytest.mark.unit
def test_system_sysdescr_accepts_runtime_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_startup(monkeypatch)
    monkeypatch.setenv(ENV_ADAPTER_HOSTNAME, "192.168.0.100")
    monkeypatch.setenv(ENV_ADAPTER_READ_COMMUNITY, "public")
    _patch_system_defaults(monkeypatch)

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
    _patch_system_defaults(monkeypatch)

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


@pytest.mark.unit
def test_system_webservice_reload_writes_sentinel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _disable_startup(monkeypatch)
    sentinel_path = tmp_path / "runtime" / "webservice.reload"
    trigger_path = tmp_path / "src" / "pypnm_cmts" / "_reload_trigger.py"
    monkeypatch.setenv(ENV_WEB_SERVICE_RELOAD_SENTINEL, str(sentinel_path))
    monkeypatch.setattr(
        "pypnm_cmts.support.web_service_reload.resolve_dev_reload_trigger_path",
        lambda: trigger_path,
    )

    with TestClient(app) as client:
        response = client.post("/cmts/system/webService/reload")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == ServiceStatusCode.SUCCESS.value
    assert payload["reload_requested"] is True
    assert payload["sentinel_path"] == str(sentinel_path)
    assert sentinel_path.exists()
    assert trigger_path.exists()
    first_payload = sentinel_path.read_text(encoding="utf-8")
    first_trigger_payload = trigger_path.read_text(encoding="utf-8")
    assert "requested_at=" in first_payload
    assert "request_id=" in first_payload
    assert "actor=cmts.system.webService.reload" in first_payload
    assert "reason=api_reload_request" in first_payload
    assert 'RELOAD_REQUEST_ID = "' in first_trigger_payload
    assert 'RELOAD_REQUESTED_AT = "' in first_trigger_payload

    with TestClient(app) as client:
        second = client.post("/cmts/system/webService/reload")
    assert second.status_code == 200
    second_payload = sentinel_path.read_text(encoding="utf-8")
    second_trigger_payload = trigger_path.read_text(encoding="utf-8")
    assert second_payload != first_payload
    assert second_trigger_payload != first_trigger_payload

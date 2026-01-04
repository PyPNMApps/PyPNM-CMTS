# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os
import socket
import subprocess
import time

import pytest
from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.config.orchestrator_config import (
    ENV_ADAPTER_HOSTNAME,
    ENV_ADAPTER_READ_COMMUNITY,
    ENV_ADAPTER_WRITE_COMMUNITY,
)
from pypnm_cmts.sgw.runtime_state import reset_sgw_runtime_state

ENV_CMTS_HOSTNAME = "CMTS_HOSTNAME"
ENV_CMTS_SNMP_COMMUNITY = "CMTS_SNMP_V2_COMMUNITY"
ENV_LIVE_FLAG = "PYPNM_CMTS_LIVE"
ENV_MAX_WAIT_SECONDS = "CMTS_LIVE_MAX_WAIT_S"
ENV_POLL_INTERVAL_SECONDS = "CMTS_LIVE_POLL_INTERVAL_S"
PING_COUNT = 1
PING_TIMEOUT_SECONDS = 1
SOCKET_TIMEOUT_SECONDS = 1.0
FALLBACK_PORTS = (22, 80)
DEFAULT_MAX_WAIT_SECONDS = 10.0
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
CABLE_MODEM_PAGE = 1
CABLE_MODEM_PAGE_SIZE = 50
REFRESH_WAIT_SECONDS = 5.0


def _get_live_hostname() -> str:
    return os.environ.get(ENV_CMTS_HOSTNAME, "").strip()


def _get_live_community() -> str:
    return os.environ.get(ENV_CMTS_SNMP_COMMUNITY, "").strip()


def _require_live_config() -> tuple[str, str]:
    if os.environ.get(ENV_LIVE_FLAG, "") != "1":
        pytest.skip("PYPNM_CMTS_LIVE=1 not set; skipping live integration tests")
    hostname = _get_live_hostname()
    if hostname == "":
        pytest.skip(f"{ENV_CMTS_HOSTNAME} not set; skipping live integration tests")
    community = _get_live_community()
    if community == "":
        pytest.skip(f"{ENV_CMTS_SNMP_COMMUNITY} not set; skipping live integration tests")
    if not _is_reachable(hostname):
        pytest.skip(f"CMTS {hostname} not reachable; skipping live integration tests")
    return (hostname, community)


def _is_reachable(host: str) -> bool:
    if _ping_host(host):
        return True
    return _socket_reachable(host)


def _ping_host(host: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT_SECONDS), host],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def _socket_reachable(host: str) -> bool:
    return any(_socket_reachable_port(host, port) for port in FALLBACK_PORTS)


def _socket_reachable_port(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


def _apply_live_env(monkeypatch: pytest.MonkeyPatch, hostname: str, community: str) -> None:
    monkeypatch.setenv(ENV_ADAPTER_HOSTNAME, hostname)
    monkeypatch.setenv(ENV_ADAPTER_READ_COMMUNITY, community)
    monkeypatch.setenv(ENV_ADAPTER_WRITE_COMMUNITY, community)


def _system_request_body(hostname: str, community: str) -> dict[str, object]:
    return {
        "cmts": {"hostname": hostname},
        "snmp": {"snmp_v2c": {"community": community}},
    }


def _fetch_ids(client: TestClient) -> dict[str, object]:
    response = client.post("/cmts/servingGroup/get/ids", json={})
    assert response.status_code == 200
    return response.json()


def _wait_for_ids(client: TestClient, max_wait_seconds: float, poll_interval_seconds: float) -> dict[str, object]:
    payload: dict[str, object] = {}
    deadline = time.monotonic() + float(max_wait_seconds)
    while time.monotonic() <= deadline:
        payload = _fetch_ids(client)
        discovered = payload.get("discovered_sg_ids", [])
        if discovered:
            return payload
        time.sleep(float(poll_interval_seconds))
    return payload


def _skip_if_empty_topology(payload: dict[str, object], message: str) -> None:
    ds_channels = payload.get("topology", {}).get("ds_channels", {})
    us_channels = payload.get("topology", {}).get("us_channels", {})
    ds_count = ds_channels.get("count", 0)
    us_count = us_channels.get("count", 0)
    if int(ds_count) == 0 and int(us_count) == 0:
        pytest.skip(message)


def _resolve_wait_seconds(env_name: str, default_value: float) -> float:
    raw_value = os.environ.get(env_name, "").strip()
    if raw_value == "":
        return default_value
    try:
        value = float(raw_value)
    except ValueError:
        return default_value
    if value <= 0:
        return default_value
    return value


def _build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    hostname, community = _require_live_config()
    _apply_live_env(monkeypatch, hostname, community)
    from pypnm_cmts.api.main import app

    return TestClient(app)


@pytest.mark.integration
@pytest.mark.slow
def test_live_serving_group_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    max_wait_seconds = _resolve_wait_seconds(ENV_MAX_WAIT_SECONDS, DEFAULT_MAX_WAIT_SECONDS)
    poll_interval_seconds = _resolve_wait_seconds(ENV_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
    with _build_client(monkeypatch) as client:
        payload = _wait_for_ids(client, max_wait_seconds, poll_interval_seconds)

    assert payload["status"] == ServiceStatusCode.SUCCESS.value
    discovered = payload.get("discovered_sg_ids", [])
    assert isinstance(discovered, list)
    summaries = payload.get("summaries", [])
    if not discovered:
        pytest.skip("no SG IDs discovered yet; SGW may still be initializing")
    assert len(summaries) == len(discovered)
    for summary in summaries:
        refresh_state = summary["metadata"]["refresh_state"]
        assert refresh_state in ("OK", "STALE", "ERROR")


@pytest.mark.integration
@pytest.mark.slow
def test_live_serving_group_topology(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    max_wait_seconds = _resolve_wait_seconds(ENV_MAX_WAIT_SECONDS, DEFAULT_MAX_WAIT_SECONDS)
    poll_interval_seconds = _resolve_wait_seconds(ENV_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
    with _build_client(monkeypatch) as client:
        payload = _wait_for_ids(client, max_wait_seconds, poll_interval_seconds)
        discovered = payload.get("discovered_sg_ids", [])
        if not discovered:
            pytest.skip("no SG IDs discovered yet; SGW may still be initializing")
        sg_id = discovered[0]
        response = client.post("/cmts/servingGroup/get/topology", json={"sg_id": sg_id})
        assert response.status_code == 200
        body = response.json()
        assert body["topology"]["sg_id"] == sg_id


@pytest.mark.integration
@pytest.mark.slow
def test_live_serving_group_topology_heavy_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    max_wait_seconds = _resolve_wait_seconds(ENV_MAX_WAIT_SECONDS, DEFAULT_MAX_WAIT_SECONDS)
    poll_interval_seconds = _resolve_wait_seconds(ENV_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
    with _build_client(monkeypatch) as client:
        payload = _wait_for_ids(client, max_wait_seconds, poll_interval_seconds)
        discovered = payload.get("discovered_sg_ids", [])
        if not discovered:
            pytest.skip("no SG IDs discovered yet; SGW may still be initializing")
        sg_id = discovered[0]
        response = client.post(
            "/cmts/servingGroup/get/topology",
            json={
                "sg_id": sg_id,
                "refresh": "heavy",
                "require_fresh": True,
                "max_wait_seconds": REFRESH_WAIT_SECONDS,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["topology"]["sg_id"] == sg_id
        _skip_if_empty_topology(body, "topology not populated yet; SGW pollers may be stubbed")


@pytest.mark.integration
@pytest.mark.slow
def test_live_serving_group_cable_modems(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    max_wait_seconds = _resolve_wait_seconds(ENV_MAX_WAIT_SECONDS, DEFAULT_MAX_WAIT_SECONDS)
    poll_interval_seconds = _resolve_wait_seconds(ENV_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
    with _build_client(monkeypatch) as client:
        payload = _wait_for_ids(client, max_wait_seconds, poll_interval_seconds)
        discovered = payload.get("discovered_sg_ids", [])
        if not discovered:
            pytest.skip("no SG IDs discovered yet; SGW may still be initializing")
        sg_id = discovered[0]
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"sg_id": sg_id, "page": CABLE_MODEM_PAGE, "page_size": CABLE_MODEM_PAGE_SIZE},
        )
        assert response.status_code == 200
        body = response.json()
        items = body.get("items", [])
        if items:
            macs = [item["mac"] for item in items]
            assert macs == sorted(macs)
        assert body["total_count"] >= len(items)


@pytest.mark.integration
@pytest.mark.slow
def test_live_serving_group_cable_modems_heavy_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    max_wait_seconds = _resolve_wait_seconds(ENV_MAX_WAIT_SECONDS, DEFAULT_MAX_WAIT_SECONDS)
    poll_interval_seconds = _resolve_wait_seconds(ENV_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
    with _build_client(monkeypatch) as client:
        payload = _wait_for_ids(client, max_wait_seconds, poll_interval_seconds)
        discovered = payload.get("discovered_sg_ids", [])
        if not discovered:
            pytest.skip("no SG IDs discovered yet; SGW may still be initializing")
        sg_id = discovered[0]
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={
                "sg_id": sg_id,
                "page": CABLE_MODEM_PAGE,
                "page_size": CABLE_MODEM_PAGE_SIZE,
                "refresh": "heavy",
                "require_fresh": True,
                "max_wait_seconds": REFRESH_WAIT_SECONDS,
            },
        )
        assert response.status_code == 200
        body = response.json()
        if body.get("total_count", 0) == 0:
            pytest.skip("membership not populated yet; SGW pollers may be stubbed")
        items = body.get("items", [])
        if items:
            macs = [item["mac"] for item in items]
            assert macs == sorted(macs)
        assert body["total_count"] >= len(items)


@pytest.mark.integration
@pytest.mark.slow
def test_live_system_sysdescr(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    hostname, community = _require_live_config()
    _apply_live_env(monkeypatch, hostname, community)
    from pypnm_cmts.api.main import app

    with TestClient(app) as client:
        response = client.post("/system/sysDescr", json=_system_request_body(hostname, community))
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        results = payload.get("results", {})
        assert results.get("raw", "") != ""
        assert results.get("is_empty") is False


@pytest.mark.integration
@pytest.mark.slow
def test_live_system_service_group_topology(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    hostname, community = _require_live_config()
    _apply_live_env(monkeypatch, hostname, community)
    from pypnm_cmts.api.main import app

    with TestClient(app) as client:
        response = client.post("/system/serviceGroupTopology", json=_system_request_body(hostname, community))
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        results = payload.get("results", [])
        assert results
        assert results[0].get("md_cm_sg_id") is not None

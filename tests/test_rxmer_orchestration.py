# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
from typing import TypeAlias

import pytest
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.config.system_config_settings import SystemConfigSettings

from pypnm_cmts.api.common.service.pnm import PnmHttpClient, PnmHttpResponseModel
from pypnm_cmts.api.routes.pnm.rxmer.schemas import RxMerServiceGroupCaptureRequest
from pypnm_cmts.api.routes.pnm.rxmer.service import (
    RXMER_ENDPOINT_PATH,
    RxMerServiceGroupCaptureService,
)
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.config.request_defaults import (
    ENV_CM_SNMPV2C_WRITE_COMMUNITY,
    ENV_CM_TFTP_IPV4,
    ENV_CM_TFTP_IPV6,
)
from pypnm_cmts.lib.constants import PnmCaptureFailureReason, PnmCaptureStatus
from pypnm_cmts.lib.types import CmtsCmRegState, ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwSnapshotModel,
)
from pypnm_cmts.sgw.runtime_state import (
    reset_sgw_runtime_state,
    set_sgw_startup_success,
)
from pypnm_cmts.sgw.store import SgwCacheStore

SNAPSHOT_TIME_EPOCH = 1000.0
PER_MODEM_TIMEOUT_SECONDS = 0.05
OVERALL_TIMEOUT_SECONDS = 0.05
SHORT_SLEEP_SECONDS = 0.02
LONG_SLEEP_SECONDS = 0.2
PnmPayload: TypeAlias = dict[str, object]
HttpRequestRecord: TypeAlias = tuple[str, PnmPayload]


class FakePnmHttpClient(PnmHttpClient):
    """In-memory PyPNM client for RxMER service tests."""

    def __init__(self, responses: list[PnmHttpResponseModel]) -> None:
        self._responses = list(responses)
        self.requests: list[HttpRequestRecord] = []

    async def __aenter__(self) -> FakePnmHttpClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post_json(self, path: str, payload: PnmPayload) -> PnmHttpResponseModel:
        self.requests.append((path, payload))
        if self._responses:
            return self._responses.pop(0)
        return PnmHttpResponseModel(
            status_code=500,
            payload={"status": ServiceStatusCode.FAILURE.value},
            error_message="",
        )


class DelayedPnmHttpClient(PnmHttpClient):
    """In-memory PyPNM client that delays responses for timeout testing."""

    def __init__(self, delay_seconds: float, response: PnmHttpResponseModel) -> None:
        self._delay_seconds = float(delay_seconds)
        self._response = response
        self.requests: list[HttpRequestRecord] = []

    async def __aenter__(self) -> DelayedPnmHttpClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post_json(self, path: str, payload: PnmPayload) -> PnmHttpResponseModel:
        self.requests.append((path, payload))
        await asyncio.sleep(self._delay_seconds)
        return self._response


class BlockingPnmHttpClient(PnmHttpClient):
    """In-memory PyPNM client that blocks until released."""

    def __init__(self, event: asyncio.Event, response: PnmHttpResponseModel) -> None:
        self._event = event
        self._response = response
        self.requests: list[HttpRequestRecord] = []

    async def __aenter__(self) -> BlockingPnmHttpClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post_json(self, path: str, payload: PnmPayload) -> PnmHttpResponseModel:
        self.requests.append((path, payload))
        await self._event.wait()
        return self._response

def _configure_runtime_state(store: SgwCacheStore, sg_id: ServiceGroupId) -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id])
    set_sgw_startup_success([sg_id], store, manager, SNAPSHOT_TIME_EPOCH)


def _seed_snapshot(store: SgwCacheStore, sg_id: ServiceGroupId, modems: list[SgwCableModemModel]) -> None:
    metadata = SgwCacheMetadataModel(snapshot_time_epoch=SNAPSHOT_TIME_EPOCH, age_seconds=0.0)
    snapshot = SgwSnapshotModel(sg_id=sg_id, cable_modems=modems, metadata=metadata)
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))


@pytest.mark.asyncio
async def test_rxmer_capture_passes_channel_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=200,
            payload={
                "status": ServiceStatusCode.SUCCESS.value,
                "message": "ok",
                "transaction_id": "tx-123",
                "operation_id": "op-456",
            },
            error_message="",
        )
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {
                "serving_group": {"id": [int(sg_id)]},
                "cable_modem": {"pnm_parameters": {"capture": {"channel_ids": [194, 193]}}},
            },
            "execution": {"max_workers": 1, "retry_count": 0, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.requested_sg_id == sg_id
    assert [int(channel_id) for channel_id in response.requested_channel_ids] == [194, 193]
    assert response.total_modems == 1
    assert response.eligible_modems == 1
    assert response.started_modems == 1
    assert response.success_modems == 1
    assert response.failed_modems == 0
    assert response.skipped_modems == 0
    assert response.summary.requested_count == 1
    assert response.summary.attempted_count == 1
    assert response.summary.success_count == 1
    assert response.summary.failure_count == 0
    assert response.results[0].status == PnmCaptureStatus.SUCCESS

    assert len(http_client.requests) == 1
    path, payload = http_client.requests[0]
    assert path == RXMER_ENDPOINT_PATH
    capture = payload["cable_modem"]["pnm_parameters"]["capture"]
    assert capture["channel_ids"] == [194, 193]


@pytest.mark.asyncio
async def test_rxmer_capture_normalizes_hex_ipv4(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="0xac132094",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=200,
            payload={"status": ServiceStatusCode.SUCCESS.value},
            error_message="",
        )
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {"max_workers": 1, "retry_count": 0, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.results[0].ipv4 == "172.19.32.148"
    _, payload = http_client.requests[0]
    assert payload["cable_modem"]["ip_address"] == "172.19.32.148"


@pytest.mark.asyncio
async def test_rxmer_capture_omits_capture_without_channel_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=200,
            payload={"status": ServiceStatusCode.SUCCESS.value},
            error_message="",
        )
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {"max_workers": 1, "retry_count": 0, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.success_modems == 1
    assert len(http_client.requests) == 1
    _, payload = http_client.requests[0]
    pnm_parameters = payload["cable_modem"]["pnm_parameters"]
    assert "capture" not in pnm_parameters


@pytest.mark.asyncio
async def test_rxmer_capture_honors_mac_filter_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modems = [
        SgwCableModemModel(
            mac="aa:bb:cc:dd:ee:ff",
            ipv4="192.168.0.100",
            ipv6="",
            registration_status=CmtsCmRegState(8),
        ),
        SgwCableModemModel(
            mac="aa:bb:cc:dd:ee:10",
            ipv4="192.168.0.101",
            ipv6="",
            registration_status=CmtsCmRegState(8),
        ),
    ]
    _seed_snapshot(store, sg_id, modems)
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=200,
            payload={"status": ServiceStatusCode.SUCCESS.value},
            error_message="",
        )
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {
                "serving_group": {"id": [int(sg_id)]},
                "cable_modem": {"mac_address": ["aa:bb:cc:dd:ee:ff"]},
            },
            "execution": {"max_workers": 1, "retry_count": 0, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.total_modems == 1
    assert response.eligible_modems == 1
    assert response.started_modems == 1
    assert response.success_modems == 1
    assert response.failed_modems == 0
    assert response.skipped_modems == 0
    assert response.summary.requested_count == 1
    assert response.summary.attempted_count == 1


@pytest.mark.asyncio
async def test_rxmer_capture_skips_modem_without_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    http_client = FakePnmHttpClient([])
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {"max_workers": 1, "retry_count": 0, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.skipped_modems == 1
    assert response.results[0].status == PnmCaptureStatus.SKIPPED
    assert response.results[0].message == "no modem ip address available"


@pytest.mark.asyncio
async def test_rxmer_capture_sends_null_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.delenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, raising=False)
    monkeypatch.delenv(ENV_CM_TFTP_IPV4, raising=False)
    monkeypatch.delenv(ENV_CM_TFTP_IPV6, raising=False)
    monkeypatch.setattr(SystemConfigSettings, "snmp_write_community", staticmethod(lambda: ""))
    monkeypatch.setattr(SystemConfigSettings, "bulk_tftp_ip_v4", staticmethod(lambda: ""))
    monkeypatch.setattr(SystemConfigSettings, "bulk_tftp_ip_v6", staticmethod(lambda: ""))

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=200,
            payload={
                "status": ServiceStatusCode.SUCCESS.value,
                "message": "ok",
                "transaction_id": "tx-123",
            },
            error_message="",
        )
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {"max_workers": 1, "retry_count": 0, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.success_modems == 1
    assert len(http_client.requests) == 1
    _, payload = http_client.requests[0]
    tftp_payload = payload["cable_modem"]["pnm_parameters"]["tftp"]
    snmp_payload = payload["cable_modem"]["snmp"]["snmpV2C"]
    assert tftp_payload["ipv4"] is None
    assert tftp_payload["ipv6"] is None
    assert snmp_payload["community"] is None


@pytest.mark.asyncio
async def test_rxmer_capture_retries_on_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=200,
            payload={"status": ServiceStatusCode.NOT_READY_AFTER_FILE_CAPTURE.value, "message": "busy"},
            error_message="",
        ),
        PnmHttpResponseModel(
            status_code=200,
            payload={"status": ServiceStatusCode.NOT_READY_AFTER_FILE_CAPTURE.value, "message": "busy"},
            error_message="",
        ),
        PnmHttpResponseModel(
            status_code=200,
            payload={
                "status": ServiceStatusCode.SUCCESS.value,
                "message": "ok",
                "transaction_id": "tx-789",
            },
            error_message="",
        ),
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {
                "serving_group": {"id": [int(sg_id)]},
            },
            "execution": {"max_workers": 1, "retry_count": 2, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.results[0].status == PnmCaptureStatus.SUCCESS
    assert response.results[0].attempts == 3
    assert len(http_client.requests) == 3


@pytest.mark.asyncio
async def test_rxmer_capture_retries_on_http_status(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    responses = [
        PnmHttpResponseModel(
            status_code=503,
            payload={},
            error_message="",
        ),
        PnmHttpResponseModel(
            status_code=200,
            payload={"status": ServiceStatusCode.SUCCESS.value},
            error_message="",
        ),
    ]
    http_client = FakePnmHttpClient(responses)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {"max_workers": 1, "retry_count": 1, "retry_delay_seconds": 0.0},
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.results[0].attempts == 2
    assert len(http_client.requests) == 2


@pytest.mark.asyncio
async def test_rxmer_capture_per_modem_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    response_payload = PnmHttpResponseModel(
        status_code=200,
        payload={"status": ServiceStatusCode.SUCCESS.value},
        error_message="",
    )
    http_client = DelayedPnmHttpClient(LONG_SLEEP_SECONDS, response_payload)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {
                "max_workers": 1,
                "retry_count": 0,
                "retry_delay_seconds": 0.0,
                "per_modem_timeout_seconds": PER_MODEM_TIMEOUT_SECONDS,
                "overall_timeout_seconds": 0.0,
            },
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.failed_modems == 1
    assert response.summary.failure_count == 1
    assert response.summary.failures_by_reason[PnmCaptureFailureReason.PER_MODEM_TIMEOUT] == 1


@pytest.mark.asyncio
async def test_rxmer_capture_overall_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modems = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.100", ipv6="", registration_status=CmtsCmRegState(8)),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:10", ipv4="192.168.0.101", ipv6="", registration_status=CmtsCmRegState(8)),
    ]
    _seed_snapshot(store, sg_id, modems)
    _configure_runtime_state(store, sg_id)

    response_payload = PnmHttpResponseModel(
        status_code=200,
        payload={"status": ServiceStatusCode.SUCCESS.value},
        error_message="",
    )
    http_client = DelayedPnmHttpClient(LONG_SLEEP_SECONDS, response_payload)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {
                "max_workers": 2,
                "retry_count": 0,
                "retry_delay_seconds": 0.0,
                "per_modem_timeout_seconds": 0.0,
                "overall_timeout_seconds": OVERALL_TIMEOUT_SECONDS,
            },
        }
    )
    response = await service.capture(request, "http://localhost/cm")

    assert response.summary.failure_count >= 1
    assert response.summary.failures_by_reason[PnmCaptureFailureReason.OVERALL_TIMEOUT] >= 1


@pytest.mark.asyncio
async def test_rxmer_capture_inflight_dedupe(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "public")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    sg_id = ServiceGroupId(3147266)
    store = SgwCacheStore()
    modem = SgwCableModemModel(
        mac="aa:bb:cc:dd:ee:ff",
        ipv4="192.168.0.100",
        ipv6="",
        registration_status=CmtsCmRegState(8),
    )
    _seed_snapshot(store, sg_id, [modem])
    _configure_runtime_state(store, sg_id)

    event = asyncio.Event()
    response_payload = PnmHttpResponseModel(
        status_code=200,
        payload={"status": ServiceStatusCode.SUCCESS.value},
        error_message="",
    )
    http_client = BlockingPnmHttpClient(event, response_payload)
    service = RxMerServiceGroupCaptureService(http_client=http_client)

    request = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {"serving_group": {"id": [int(sg_id)]}},
            "execution": {
                "max_workers": 1,
                "retry_count": 0,
                "retry_delay_seconds": 0.0,
                "per_modem_timeout_seconds": 0.0,
                "overall_timeout_seconds": 0.0,
            },
        }
    )
    request_with_channel_ids = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {
                "serving_group": {"id": [int(sg_id)]},
                "cable_modem": {"pnm_parameters": {"capture": {"channel_ids": [194, 193]}}},
            },
            "execution": {
                "max_workers": 1,
                "retry_count": 0,
                "retry_delay_seconds": 0.0,
                "per_modem_timeout_seconds": 0.0,
                "overall_timeout_seconds": 0.0,
            },
        }
    )
    request_with_channel_ids_reversed = RxMerServiceGroupCaptureRequest.model_validate(
        {
            "cmts": {
                "serving_group": {"id": [int(sg_id)]},
                "cable_modem": {"pnm_parameters": {"capture": {"channel_ids": [193, 194]}}},
            },
            "execution": {
                "max_workers": 1,
                "retry_count": 0,
                "retry_delay_seconds": 0.0,
                "per_modem_timeout_seconds": 0.0,
                "overall_timeout_seconds": 0.0,
            },
        }
    )
    capture_task = asyncio.create_task(service.capture(request, "http://localhost/cm"))
    await asyncio.sleep(SHORT_SLEEP_SECONDS)

    duplicate_response = await service.capture(request, "http://localhost/cm")
    assert duplicate_response.already_running is True
    assert duplicate_response.run_id != ""

    event.set()
    response = await capture_task
    assert response.already_running is False
    assert response.run_id == duplicate_response.run_id

    event = asyncio.Event()
    http_client = BlockingPnmHttpClient(event, response_payload)
    service = RxMerServiceGroupCaptureService(http_client=http_client)
    capture_task = asyncio.create_task(service.capture(request_with_channel_ids, "http://localhost/cm"))
    await asyncio.sleep(SHORT_SLEEP_SECONDS)
    duplicate_response = await service.capture(request_with_channel_ids_reversed, "http://localhost/cm")
    assert duplicate_response.already_running is True
    assert duplicate_response.run_id != ""

    event.set()
    response = await capture_task
    assert response.already_running is False
    assert response.run_id == duplicate_response.run_id

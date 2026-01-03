# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.main import app
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel, SgwRefreshState
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwChannelSummaryModel,
    SgwSnapshotModel,
)
from pypnm_cmts.sgw.runtime_state import (
    reset_sgw_runtime_state,
    set_sgw_startup_success,
)
from pypnm_cmts.sgw.store import SgwCacheStore

SG_ID_ONE = ServiceGroupId(1)
SG_ID_TWO = ServiceGroupId(2)
DISCOVERED_SG_IDS = [SG_ID_ONE, SG_ID_TWO]
SNAPSHOT_TIME_EPOCH = 1000.0
AGE_SECONDS = 10.0


async def _noop() -> None:
    return


def _disable_startup(monkeypatch: object) -> None:
    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)


def _seed_store(
    store: SgwCacheStore,
    sg_id: ServiceGroupId,
    modems: list[SgwCableModemModel],
    ds_channels: SgwChannelSummaryModel | None = None,
    us_channels: SgwChannelSummaryModel | None = None,
) -> None:
    metadata = SgwCacheMetadataModel(
        snapshot_time_epoch=SNAPSHOT_TIME_EPOCH,
        age_seconds=AGE_SECONDS,
    )
    snapshot = SgwSnapshotModel(
        sg_id=sg_id,
        ds_channels=ds_channels or SgwChannelSummaryModel(),
        us_channels=us_channels or SgwChannelSummaryModel(),
        cable_modems=modems,
        metadata=metadata,
    )
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))


def _configure_runtime_state(store: SgwCacheStore, sg_ids: list[ServiceGroupId]) -> None:
    settings = CmtsOrchestratorSettings()
    manager = SgwManager(settings=settings, store=store, service_groups=sg_ids)
    set_sgw_startup_success(sg_ids, store, manager, SNAPSHOT_TIME_EPOCH)


def test_serving_group_ids_returns_cache_summary(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _seed_store(store, SG_ID_TWO, [])
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/ids", json={})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["discovered_sg_ids"] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert payload["sgw_ready"] is True
        summaries = payload["summaries"]
        assert len(summaries) == 2
        assert summaries[0]["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


def test_serving_group_ids_not_ready_returns_success(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/ids", json={})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["sgw_ready"] is False
        assert "sgw cache not ready" in payload["message"]
        summaries = payload["summaries"]
        assert summaries[1]["metadata"]["refresh_state"] == SgwRefreshState.ERROR.value
        assert summaries[1]["metadata"]["last_error"] != ""


def test_serving_group_ids_missing_store_returns_error_metadata(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _configure_runtime_state(store, [SG_ID_ONE])

    monkeypatch.setattr("pypnm_cmts.api.routes.serving_group.service.get_sgw_store", lambda: None)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/ids", json={})
        assert response.status_code == 200
        payload = response.json()
        summaries = payload["summaries"]
        assert summaries[0]["metadata"]["refresh_state"] == SgwRefreshState.ERROR.value
        assert summaries[0]["metadata"]["last_error"] != ""


def test_serving_group_cable_modems_requires_sg_id(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/cableModems", json={})
        assert response.status_code == 422


def test_serving_group_cable_modems_pagination(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_ONE
    page_one = 1
    page_two = 2
    page_size = 2
    total_count = 3
    modems = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01"),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:03"),
    ]
    _seed_store(store, sg_id, modems)
    _configure_runtime_state(store, [sg_id])

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"sg_id": int(sg_id), "page": page_one, "page_size": page_size},
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["total_count"] == total_count
        assert [item["mac"] for item in payload["items"]] == [
            "aa:bb:cc:dd:ee:01",
            "aa:bb:cc:dd:ee:02",
        ]

        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"sg_id": int(sg_id), "page": page_two, "page_size": page_size},
        )
        payload = response.json()
        assert [item["mac"] for item in payload["items"]] == [
            "aa:bb:cc:dd:ee:03",
        ]
        assert payload["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


def test_serving_group_cable_modems_missing_store_returns_error(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"sg_id": int(SG_ID_ONE), "page": 1, "page_size": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.FAILURE.value
        assert payload["metadata"]["refresh_state"] == SgwRefreshState.ERROR.value
        assert payload["metadata"]["last_error"] != ""


def test_serving_group_topology_requires_sg_id(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/topology", json={})
        assert response.status_code == 422


def test_serving_group_topology_returns_summary(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_TWO
    ds_channel_count = 1
    us_channel_count = 2
    ds_channel_id = 100
    us_channel_id_primary = 200
    us_channel_id_secondary = 201
    ds_channels = SgwChannelSummaryModel(count=ds_channel_count, channel_ids=[ds_channel_id])
    us_channels = SgwChannelSummaryModel(count=us_channel_count, channel_ids=[us_channel_id_primary, us_channel_id_secondary])
    _seed_store(store, sg_id, [], ds_channels=ds_channels, us_channels=us_channels)
    _configure_runtime_state(store, [sg_id])

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/topology", json={"sg_id": int(sg_id)})
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["topology"]["ds_channels"]["count"] == ds_channel_count
        assert payload["topology"]["us_channels"]["count"] == us_channel_count
        assert payload["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


def test_serving_group_metadata_age_seconds_uses_request_time(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_ONE
    now_epoch = SNAPSHOT_TIME_EPOCH + 5.0
    _seed_store(store, sg_id, [])
    _configure_runtime_state(store, [sg_id])

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.service.ServingGroupCacheService._now_epoch",
        staticmethod(lambda: now_epoch),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"sg_id": int(sg_id), "page": 1, "page_size": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["metadata"]["age_seconds"] == 5.0
        entry = store.get_entry(sg_id)
        assert entry is not None
        assert entry.snapshot.metadata.age_seconds == AGE_SECONDS

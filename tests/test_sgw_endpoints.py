# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.main import app
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import CacheRefreshMode
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


@pytest.mark.unit
def test_serving_group_status_reports_cache_readiness(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.get("/cmts/servingGroup/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["discovered_count"] == len(DISCOVERED_SG_IDS)
        assert payload["cache_ready"] is False
        assert payload["missing_sg_ids"] == [int(SG_ID_TWO)]
        assert payload["refresh_running"] is False


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


def test_serving_group_cable_modems_aggregate_dedupes(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    modems_sg1 = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01"),
    ]
    modems_sg2 = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01"),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:03"),
    ]
    _seed_store(store, SG_ID_ONE, modems_sg1)
    _seed_store(store, SG_ID_TWO, modems_sg2)
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"sg_id": 0, "page": 1, "page_size": 10},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["sg_ids"] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert [item["mac"] for item in payload["items"]] == [
            "aa:bb:cc:dd:ee:01",
            "aa:bb:cc:dd:ee:02",
            "aa:bb:cc:dd:ee:03",
        ]


def test_serving_group_topology_aggregate_dedupes(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    ds_channels_sg1 = SgwChannelSummaryModel(count=2, channel_ids=[100, 101])
    us_channels_sg1 = SgwChannelSummaryModel(count=1, channel_ids=[200])
    ds_channels_sg2 = SgwChannelSummaryModel(count=2, channel_ids=[101, 102])
    us_channels_sg2 = SgwChannelSummaryModel(count=2, channel_ids=[200, 201])
    _seed_store(store, SG_ID_ONE, [], ds_channels=ds_channels_sg1, us_channels=us_channels_sg1)
    _seed_store(store, SG_ID_TWO, [], ds_channels=ds_channels_sg2, us_channels=us_channels_sg2)
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/topology", json={"sg_id": 0})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["sg_ids"] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert payload["topology"]["ds_channels"]["count"] == 3
        assert payload["topology"]["us_channels"]["count"] == 2
        assert payload["topology"]["ds_channels"]["channel_ids"] == [100, 101, 102]
        assert payload["topology"]["us_channels"]["channel_ids"] == [200, 201]


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


def test_serving_group_refresh_waits_for_snapshot(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_ONE
    now_epoch = SNAPSHOT_TIME_EPOCH
    new_epoch = SNAPSHOT_TIME_EPOCH + 5.0
    _seed_store(store, sg_id, [])
    _configure_runtime_state(store, [sg_id])

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.service.ServingGroupCacheService._now_epoch",
        staticmethod(lambda: now_epoch),
    )
    monotonic_calls = {"value": 0.0}

    def _monotonic() -> float:
        monotonic_calls["value"] += 0.2
        return monotonic_calls["value"]

    def _sleep(_seconds: float) -> None:
        entry = store.get_entry(sg_id)
        assert entry is not None
        metadata = entry.snapshot.metadata.model_copy(update={"snapshot_time_epoch": new_epoch})
        entry.snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
        store.upsert_entry(entry)

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.service.ServingGroupCacheService._monotonic",
        staticmethod(_monotonic),
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.service.ServingGroupCacheService._sleep",
        staticmethod(_sleep),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={
                "sg_id": int(sg_id),
                "page": 1,
                "page_size": 1,
                "refresh": CacheRefreshMode.HEAVY.value,
                "require_fresh": True,
                "max_wait_seconds": 1.0,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["refresh_applied"] is True
        assert payload["waited_seconds"] > 0.0
        assert payload["metadata"]["snapshot_time_epoch"] == new_epoch


def test_serving_group_refresh_rate_limited(monkeypatch: object) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    settings = CmtsOrchestratorSettings()
    poll_heavy_seconds = int(settings.sgw.poll_heavy_seconds)
    now_epoch = SNAPSHOT_TIME_EPOCH
    last_heavy_epoch = now_epoch - float(poll_heavy_seconds) + 1.0
    metadata = SgwCacheMetadataModel(
        snapshot_time_epoch=SNAPSHOT_TIME_EPOCH,
        age_seconds=AGE_SECONDS,
        last_heavy_refresh_epoch=last_heavy_epoch,
    )
    snapshot = SgwSnapshotModel(sg_id=SG_ID_ONE, metadata=metadata)
    store.upsert_entry(SgwCacheEntryModel(sg_id=SG_ID_ONE, snapshot=snapshot))
    manager = SgwManager(settings=settings, store=store, service_groups=[SG_ID_ONE])
    set_sgw_startup_success([SG_ID_ONE], store, manager, SNAPSHOT_TIME_EPOCH)

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.service.ServingGroupCacheService._now_epoch",
        staticmethod(lambda: now_epoch),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={
                "sg_id": int(SG_ID_ONE),
                "page": 1,
                "page_size": 1,
                "refresh": CacheRefreshMode.HEAVY.value,
                "require_fresh": False,
                "max_wait_seconds": 0.0,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["refresh_applied"] is False
        assert payload["metadata"]["refresh_state"] == SgwRefreshState.ERROR.value
        assert "rate limited" in payload["metadata"]["last_error"]

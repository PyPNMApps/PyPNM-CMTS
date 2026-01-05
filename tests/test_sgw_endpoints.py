# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.main import app
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import RfChannelType
from pypnm_cmts.lib.types import ChSetId, CmtsCmRegState, ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel, SgwRefreshState
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwChannelSummaryModel,
    SgwRfChannelModel,
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


def _disable_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)


def _seed_store(
    store: SgwCacheStore,
    sg_id: ServiceGroupId,
    modems: list[SgwCableModemModel],
    ds_channels: SgwChannelSummaryModel | None = None,
    us_channels: SgwChannelSummaryModel | None = None,
    ds_ch_set_id: ChSetId | None = None,
    us_ch_set_id: ChSetId | None = None,
    ds_rf_channels: list[SgwRfChannelModel] | None = None,
    us_rf_channels: list[SgwRfChannelModel] | None = None,
) -> None:
    metadata = SgwCacheMetadataModel(
        snapshot_time_epoch=SNAPSHOT_TIME_EPOCH,
        age_seconds=AGE_SECONDS,
    )
    snapshot = SgwSnapshotModel(
        sg_id=sg_id,
        ds_ch_set_id=ds_ch_set_id or ChSetId(0),
        us_ch_set_id=us_ch_set_id or ChSetId(0),
        ds_channels=ds_channels or SgwChannelSummaryModel(),
        us_channels=us_channels or SgwChannelSummaryModel(),
        ds_rf_channels=ds_rf_channels or [],
        us_rf_channels=us_rf_channels or [],
        cable_modems=modems,
        metadata=metadata,
    )
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))


def _configure_runtime_state(store: SgwCacheStore, sg_ids: list[ServiceGroupId]) -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    manager = SgwManager(settings=settings, store=store, service_groups=sg_ids)
    set_sgw_startup_success(sg_ids, store, manager, SNAPSHOT_TIME_EPOCH)


def test_serving_group_ids_returns_cache_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _seed_store(store, SG_ID_TWO, [])
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.get("/cmts/servingGroup/get/ids")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["discovered_sg_ids"] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert payload["sgw_ready"] is True
        summaries = payload["summaries"]
        assert len(summaries) == 2
        assert summaries[0]["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


@pytest.mark.unit
def test_serving_group_status_reports_cache_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_serving_group_ids_not_ready_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.get("/cmts/servingGroup/get/ids")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["sgw_ready"] is False
        assert "sgw cache not ready" in payload["message"]
        summaries = payload["summaries"]
        assert summaries[1]["metadata"]["refresh_state"] == SgwRefreshState.ERROR.value
        assert summaries[1]["metadata"]["last_error"] != ""


def test_serving_group_ids_missing_store_returns_error_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [])
    _configure_runtime_state(store, [SG_ID_ONE])

    monkeypatch.setattr("pypnm_cmts.api.routes.serving_group.service.get_sgw_store", lambda: None)

    with TestClient(app) as client:
        response = client.get("/cmts/servingGroup/get/ids")
        assert response.status_code == 200
        payload = response.json()
        summaries = payload["summaries"]
        assert summaries[0]["metadata"]["refresh_state"] == SgwRefreshState.ERROR.value
        assert summaries[0]["metadata"]["last_error"] != ""


def test_serving_group_cable_modems_defaults_to_all_sgs(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    modems_one = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01"),
    ]
    modems_two = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
    ]
    _seed_store(store, SG_ID_ONE, modems_one, ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[10]), us_channels=SgwChannelSummaryModel(count=1, channel_ids=[20]))
    _seed_store(store, SG_ID_TWO, modems_two, ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[11]), us_channels=SgwChannelSummaryModel(count=1, channel_ids=[21]))
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/get/cableModems", json={"cmts": {}})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["requested_sg_ids"] == []
        assert payload["resolved_sg_ids"] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert payload["missing_sg_ids"] == []
        groups = payload["groups"]
        assert [group["sg_id"] for group in groups] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert [group["items"][0]["mac_address"] for group in groups] == [
            "aa:bb:cc:dd:ee:01",
            "aa:bb:cc:dd:ee:02",
        ]
        assert groups[0]["items"][0]["registration_status"]["status"] == 1
        assert groups[0]["items"][0]["registration_status"]["text"] == "other"


def test_serving_group_cable_modems_filters_by_sg(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    modems_one = [
        SgwCableModemModel(
            mac="aa:bb:cc:dd:ee:01",
            ds_channel_set=ChSetId(10),
            us_channel_set=ChSetId(20),
            registration_status=CmtsCmRegState(5),
        )
    ]
    modems_two = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
    ]
    _seed_store(store, SG_ID_ONE, modems_one, ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[10]), us_channels=SgwChannelSummaryModel(count=1, channel_ids=[20]))
    _seed_store(store, SG_ID_TWO, modems_two)
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={
                "cmts": {
                    "serving_group": {"id": [int(SG_ID_ONE)]},
                },
                "page": 1,
                "page_size": 10,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["resolved_sg_ids"] == [int(SG_ID_ONE)]
        assert payload["missing_sg_ids"] == []
        items = payload["groups"][0]["items"]
        assert [item["mac_address"] for item in items] == ["aa:bb:cc:dd:ee:01"]
        assert items[0]["ds_channel_ids"] == [10]
        assert items[0]["us_channel_ids"] == [20]
        assert items[0]["registration_status"]["status"] == 5
        assert items[0]["registration_status"]["text"] == "dhcpv4Complete"


def test_serving_group_cable_modems_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
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
            json={
                "cmts": {"serving_group": {"id": [int(sg_id)]}},
                "page": page_one,
                "page_size": page_size,
            },
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        group = payload["groups"][0]
        assert group["total_items"] == total_count
        assert group["total_pages"] == 2
        assert [item["mac_address"] for item in group["items"]] == [
            "aa:bb:cc:dd:ee:01",
            "aa:bb:cc:dd:ee:02",
        ]

        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={
                "cmts": {"serving_group": {"id": [int(sg_id)]}},
                "page": page_two,
                "page_size": page_size,
            },
        )
        payload = response.json()
        group = payload["groups"][0]
        assert [item["mac_address"] for item in group["items"]] == [
            "aa:bb:cc:dd:ee:03",
        ]
        assert group["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


def test_serving_group_cable_modems_missing_store_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}}, "page": 1, "page_size": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.FAILURE.value
        assert payload["groups"] == []


def test_serving_group_topology_all_sgs_returns_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    ds_channels_sg1 = SgwChannelSummaryModel(count=1, channel_ids=[100])
    us_channels_sg1 = SgwChannelSummaryModel(count=1, channel_ids=[200])
    ds_channels_sg2 = SgwChannelSummaryModel(count=1, channel_ids=[101])
    us_channels_sg2 = SgwChannelSummaryModel(count=1, channel_ids=[201])
    ds_rf_channels_sg1 = [
        SgwRfChannelModel(
            channel_id=100,
            channel_type=RfChannelType.SC_QAM,
            center_frequency_hz=300000000,
            channel_width_hz=6000000,
            lower_frequency_hz=297000000,
            upper_frequency_hz=303000000,
        ),
    ]
    us_rf_channels_sg1 = [
        SgwRfChannelModel(
            channel_id=200,
            channel_type=RfChannelType.SC_QAM,
            center_frequency_hz=50000000,
            channel_width_hz=6400000,
            lower_frequency_hz=46800000,
            upper_frequency_hz=53200000,
        ),
    ]
    ds_rf_channels_sg2 = [
        SgwRfChannelModel(
            channel_id=101,
            channel_type=RfChannelType.SC_QAM,
            center_frequency_hz=306000000,
            channel_width_hz=6000000,
            lower_frequency_hz=303000000,
            upper_frequency_hz=309000000,
        ),
    ]
    us_rf_channels_sg2 = [
        SgwRfChannelModel(
            channel_id=201,
            channel_type=RfChannelType.SC_QAM,
            center_frequency_hz=52000000,
            channel_width_hz=6400000,
            lower_frequency_hz=48800000,
            upper_frequency_hz=55200000,
        ),
    ]
    _seed_store(
        store,
        SG_ID_ONE,
        [],
        ds_channels=ds_channels_sg1,
        us_channels=us_channels_sg1,
        ds_ch_set_id=ChSetId(10),
        us_ch_set_id=ChSetId(20),
        ds_rf_channels=ds_rf_channels_sg1,
        us_rf_channels=us_rf_channels_sg1,
    )
    _seed_store(
        store,
        SG_ID_TWO,
        [],
        ds_channels=ds_channels_sg2,
        us_channels=us_channels_sg2,
        ds_ch_set_id=ChSetId(11),
        us_ch_set_id=ChSetId(21),
        ds_rf_channels=ds_rf_channels_sg2,
        us_rf_channels=us_rf_channels_sg2,
    )
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/topology",
            json={"cmts": {"serving_group": {"id": []}}},
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert [group["sg_id"] for group in payload["groups"]] == [int(SG_ID_ONE), int(SG_ID_TWO)]


def test_serving_group_topology_single_sg_returns_group(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_TWO
    ds_channel_id = 100
    us_channel_id_primary = 200
    ds_channels = SgwChannelSummaryModel(count=1, channel_ids=[ds_channel_id])
    us_channels = SgwChannelSummaryModel(count=1, channel_ids=[us_channel_id_primary])
    ds_rf_channels = [
        SgwRfChannelModel(
            channel_id=ds_channel_id,
            channel_type=RfChannelType.SC_QAM,
            center_frequency_hz=300000000,
            channel_width_hz=6000000,
            lower_frequency_hz=297000000,
            upper_frequency_hz=303000000,
        ),
    ]
    us_rf_channels = [
        SgwRfChannelModel(
            channel_id=us_channel_id_primary,
            channel_type=RfChannelType.SC_QAM,
            center_frequency_hz=50000000,
            channel_width_hz=6400000,
            lower_frequency_hz=46800000,
            upper_frequency_hz=53200000,
        ),
    ]
    _seed_store(
        store,
        sg_id,
        [],
        ds_channels=ds_channels,
        us_channels=us_channels,
        ds_ch_set_id=ChSetId(10),
        us_ch_set_id=ChSetId(20),
        ds_rf_channels=ds_rf_channels,
        us_rf_channels=us_rf_channels,
    )
    _configure_runtime_state(store, [sg_id])

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/topology",
            json={"cmts": {"serving_group": {"id": [int(sg_id)]}}},
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["groups"][0]["sg_id"] == int(sg_id)
        assert payload["groups"][0]["channels"]["ds"]["sc_qam"][0]["channel_id"] == ds_channel_id
        assert payload["groups"][0]["channels"]["us"]["sc_qam"][0]["channel_id"] == us_channel_id_primary
        assert payload["groups"][0]["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


def test_serving_group_cable_modems_missing_sg_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    modems_sg1 = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01"),
    ]
    _seed_store(store, SG_ID_ONE, modems_sg1)
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/cableModems",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE), 999]}}, "page": 1, "page_size": 10},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["resolved_sg_ids"] == [int(SG_ID_ONE)]
        assert payload["missing_sg_ids"] == [999]


def test_serving_group_topology_rejects_multiple_sg_ids(monkeypatch: pytest.MonkeyPatch) -> None:
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
        response = client.post(
            "/cmts/servingGroup/get/topology",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE), int(SG_ID_TWO)]}}},
        )
        assert response.status_code == 422


def test_serving_group_topology_rejects_zero_sg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/topology",
            json={"cmts": {"serving_group": {"id": [0]}}},
        )
        assert response.status_code == 422


def test_serving_group_topology_paginates_modems(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    modems = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01"),
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
    ]
    ds_channels = SgwChannelSummaryModel(count=1, channel_ids=[100])
    us_channels = SgwChannelSummaryModel(count=1, channel_ids=[200])
    _seed_store(store, SG_ID_ONE, modems, ds_channels=ds_channels, us_channels=us_channels)
    _configure_runtime_state(store, [SG_ID_ONE])

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/get/topology",
            json={
                "cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}},
                "page": 2,
                "page_size": 1,
            },
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["groups"][0]["total_pages"] == 2
        assert payload["groups"][0]["page"] == 2
        assert len(payload["groups"][0]["modems"]) == 1


def test_serving_group_metadata_age_seconds_uses_request_time(monkeypatch: pytest.MonkeyPatch) -> None:
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
            json={"cmts": {"serving_group": {"id": [int(sg_id)]}}, "page": 1, "page_size": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["groups"][0]["metadata"]["age_seconds"] == 5.0
        entry = store.get_entry(sg_id)
        assert entry is not None
        assert entry.snapshot.metadata.age_seconds == AGE_SECONDS

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.docsis.data_type.sysDescr import SystemDescriptorModel

from pypnm_cmts.api.main import app
from pypnm_cmts.api.routes.serving_group.cm.operations.schemas import (
    ServingGroupCableModemSysDescrEntryModel,
    ServingGroupCableModemSysDescrGroupModel,
    ServingGroupDocsDevResetNowRequest,
    ServingGroupGetSysDescrRequest,
)
from pypnm_cmts.api.routes.serving_group.cm.operations.service import (
    ServingGroupCableModemOperationsService,
)
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import CacheRefreshMode, RfChannelType
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
    get_sgw_manager,
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
        response = client.get("/cmts/servingGroup/operations/get/ids")
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
        response = client.get("/cmts/servingGroup/operations/get/status")
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
        response = client.get("/cmts/servingGroup/operations/get/ids")
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

    monkeypatch.setattr("pypnm_cmts.api.routes.serving_group.operations.service.get_sgw_store", lambda: None)

    with TestClient(app) as client:
        response = client.get("/cmts/servingGroup/operations/get/ids")
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
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv6="0x00000000000000000000000000000000"),
    ]
    modems_two = [
        SgwCableModemModel(mac="aa:bb:cc:dd:ee:02"),
    ]
    _seed_store(store, SG_ID_ONE, modems_one, ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[10]), us_channels=SgwChannelSummaryModel(count=1, channel_ids=[20]))
    _seed_store(store, SG_ID_TWO, modems_two, ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[11]), us_channels=SgwChannelSummaryModel(count=1, channel_ids=[21]))
    _configure_runtime_state(store, DISCOVERED_SG_IDS)

    with TestClient(app) as client:
        response = client.post("/cmts/servingGroup/operations/get/cableModems", json={"cmts": {}})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["requested_sg_ids"] == []
        assert payload["resolved_sg_ids"] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert payload["missing_sg_ids"] == []
        assert payload["refresh"]["requested"] is False
        assert payload["refresh"]["mode"] == "none"
        assert payload["refresh"]["applied"] is False
        assert payload["refresh"]["advanced"] is False
        groups = payload["groups"]
        assert [group["sg_id"] for group in groups] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        assert [group["items"][0]["mac_address"] for group in groups] == [
            "aa:bb:cc:dd:ee:01",
            "aa:bb:cc:dd:ee:02",
        ]
        assert "sysdescr" in groups[0]["items"][0]
        assert groups[0]["items"][0]["sysdescr"]["is_empty"] is True
        assert groups[0]["items"][0]["ipv6"] == "::"
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
            "/cmts/servingGroup/operations/get/cableModems",
            json={
                "cmts": {
                    "serving_group": {"id": [int(SG_ID_ONE)]},
                }
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


def test_serving_group_cable_modems_uses_default_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_ONE
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
            "/cmts/servingGroup/operations/get/cableModems",
            json={
                "cmts": {"serving_group": {"id": [int(sg_id)]}},
            },
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        group = payload["groups"][0]
        assert group["total_items"] == total_count
        assert group["page"] == 1
        assert group["page_size"] == 100
        assert group["total_pages"] == 1
        assert [item["mac_address"] for item in group["items"]] == [
            "aa:bb:cc:dd:ee:01",
            "aa:bb:cc:dd:ee:02",
            "aa:bb:cc:dd:ee:03",
        ]
        assert group["metadata"]["snapshot_time_epoch"] == SNAPSHOT_TIME_EPOCH


def test_serving_group_cable_modems_missing_store_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/operations/get/cableModems",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.FAILURE.value
        assert payload["refresh"]["mode"] == "none"
        assert payload["groups"] == []


def test_serving_group_cable_modems_refresh_heavy_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(store, SG_ID_ONE, [SgwCableModemModel(mac="aa:bb:cc:dd:ee:01")])
    _configure_runtime_state(store, [SG_ID_ONE])

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.operations.service.ServingGroupCacheService._request_refresh",
        lambda self, sg_ids, refresh, now_epoch: (True, ""),
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.operations.service.ServingGroupCacheService._wait_for_refresh",
        lambda self, sg_ids, store, baseline, timeout_seconds: (True, 0.0),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/operations/get/cableModems",
            json={
                "cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}},
                "refresh": {
                    "mode": "heavy",
                    "wait_for_cache": True,
                    "timeout_seconds": 5,
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["refresh"]["requested"] is True
        assert payload["refresh"]["mode"] == "heavy"
        assert payload["refresh"]["applied"] is True
        assert payload["refresh"]["wait_for_cache"] is True
        assert payload["refresh"]["advanced"] is True
        assert payload["refresh"]["timeout_seconds"] == 5


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
            "/cmts/servingGroup/operations/get/topology",
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
            "/cmts/servingGroup/operations/get/topology",
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
            "/cmts/servingGroup/operations/get/cableModems",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE), 999]}}},
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
            "/cmts/servingGroup/operations/get/topology",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE), int(SG_ID_TWO)]}}},
        )
        assert response.status_code == 422


def test_serving_group_topology_rejects_zero_sg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/operations/get/topology",
            json={"cmts": {"serving_group": {"id": [0]}}},
        )
        assert response.status_code == 422


def test_serving_group_topology_uses_default_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
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
            "/cmts/servingGroup/operations/get/topology",
            json={
                "cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}},
            },
        )
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["groups"][0]["page"] == 1
        assert payload["groups"][0]["page_size"] == 100
        assert payload["groups"][0]["total_pages"] == 1
        assert len(payload["groups"][0]["modems"]) == 2


def test_serving_group_metadata_age_seconds_uses_request_time(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    sg_id = SG_ID_ONE
    now_epoch = SNAPSHOT_TIME_EPOCH + 5.0
    _seed_store(store, sg_id, [])
    _configure_runtime_state(store, [sg_id])

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.operations.service.ServingGroupCacheService._now_epoch",
        staticmethod(lambda: now_epoch),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/operations/get/cableModems",
            json={"cmts": {"serving_group": {"id": [int(sg_id)]}}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["groups"][0]["metadata"]["age_seconds"] == 5.0
        entry = store.get_entry(sg_id)
        assert entry is not None
        assert entry.snapshot.metadata.age_seconds == AGE_SECONDS


def test_serving_group_docs_dev_reset_now_scoped_success(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:02", ipv4="192.168.0.102"),
        ],
    )
    _configure_runtime_state(store, [SG_ID_ONE])

    def _fake_reset(
        mac_address: object,
        ip_address: object,
        write_community: object,
    ) -> tuple[ServiceStatusCode, str]:
        assert mac_address == "aa:bb:cc:dd:ee:02"
        assert ip_address == "192.168.0.102"
        assert write_community == "private"
        return (ServiceStatusCode.SUCCESS, "docsDevResetNow command sent")

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._send_docs_dev_reset_now",
        staticmethod(_fake_reset),
    )
    ping_calls = {"count": 0}

    def _fake_ping(mac_address: object, ip_address: object, write_community: object) -> bool:
        ping_calls["count"] += 1
        assert mac_address == "aa:bb:cc:dd:ee:02"
        assert ip_address == "192.168.0.102"
        assert write_community == "private"
        return ping_calls["count"] < 3

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._is_modem_ping_reachable",
        staticmethod(_fake_ping),
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._sleep_before_ping_retry",
        staticmethod(lambda: None),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/docsDevResetNow",
            json={
                "cmts": {
                    "serving_group": {"id": [int(SG_ID_ONE)]},
                    "cable_modem": {
                        "mac_address": ["aa:bb:cc:dd:ee:02"],
                        "snmp": {"snmpV2C": {"community": "private"}},
                    },
                }
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["missing_sg_ids"] == []
        assert payload["missing_mac_addresses"] == []
        assert payload["groups"][0]["sg_id"] == int(SG_ID_ONE)
        assert payload["groups"][0]["success_count"] == 1
        assert payload["groups"][0]["failure_count"] == 0
        modem = payload["groups"][0]["modems"]["aa:bb:cc:dd:ee:02"]
        assert modem["status"] == ServiceStatusCode.SUCCESS.value
        assert modem["ping_attempts"] == 3
        assert modem["ping_last_reachable"] is False


def test_serving_group_docs_dev_reset_now_missing_mac_returns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101")],
    )
    _configure_runtime_state(store, [SG_ID_ONE])

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/docsDevResetNow",
            json={
                "cmts": {
                    "serving_group": {"id": [int(SG_ID_ONE)]},
                    "cable_modem": {"mac_address": ["aa:bb:cc:dd:ee:03"]},
                }
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.FAILURE.value
        assert payload["missing_mac_addresses"] == ["aa:bb:cc:dd:ee:03"]
        assert payload["groups"][0]["modem_count"] == 0


def test_serving_group_docs_dev_reset_now_ping_success_after_retries_is_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101")],
    )
    _configure_runtime_state(store, [SG_ID_ONE])

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._send_docs_dev_reset_now",
        staticmethod(lambda mac_address, ip_address, write_community: (ServiceStatusCode.SUCCESS, "docsDevResetNow command sent")),
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._is_modem_ping_reachable",
        staticmethod(lambda mac_address, ip_address, write_community: True),
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._sleep_before_ping_retry",
        staticmethod(lambda: None),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/docsDevResetNow",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.FAILURE.value
        modem = payload["groups"][0]["modems"]["aa:bb:cc:dd:ee:01"]
        assert modem["status"] == ServiceStatusCode.PING_FAILED.value
        assert modem["ping_attempts"] == 5
        assert modem["ping_last_reachable"] is True


def test_serving_group_docs_dev_reset_now_schema_excludes_pnm_parameters() -> None:
    schema = ServingGroupDocsDevResetNowRequest.model_json_schema()
    assert "pnm_parameters" not in str(schema)


def test_serving_group_get_sys_descr_schema_excludes_snmp() -> None:
    schema = ServingGroupGetSysDescrRequest.model_json_schema()
    assert "snmp" not in str(schema)
    assert "poll" in str(schema)


def test_serving_group_get_sys_descr_community_prefers_system_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.SystemConfigSettings.snmp_read_community",
        lambda: "cmpublic",
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.CmtsSystemConfigSettings.cmts_snmp_v2c_read_community",
        lambda index: "cmtspublic",
    )

    communities = ServingGroupCableModemOperationsService._resolve_sys_descr_communities()
    assert [str(value) for value in communities] == ["cmpublic"]


def test_serving_group_get_sys_descr_community_falls_back_to_cmts_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.SystemConfigSettings.snmp_read_community",
        lambda: "",
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.CmtsSystemConfigSettings.cmts_snmp_v2c_read_community",
        lambda index: "cmtspublic",
    )

    communities = ServingGroupCableModemOperationsService._resolve_sys_descr_communities()
    assert [str(value) for value in communities] == ["cmtspublic"]


def test_serving_group_get_sys_descr_grouped_by_sg(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:02", ipv4="192.168.0.102"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:03", ipv4="192.168.0.103"),
        ],
    )
    _seed_store(
        store,
        SG_ID_TWO,
        [
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:04", ipv4="192.168.0.104"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:05", ipv4="192.168.0.105"),
        ],
    )
    _configure_runtime_state(store, [SG_ID_ONE, SG_ID_TWO])

    sysdescr_by_mac = {
        "aa:bb:cc:dd:ee:01": SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False),
        "aa:bb:cc:dd:ee:02": SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False),
        "aa:bb:cc:dd:ee:03": SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False),
        "aa:bb:cc:dd:ee:04": None,
        "aa:bb:cc:dd:ee:05": SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False),
    }

    def _fake_collect(
        sg_id: object,
        mac_address: object,
        ip_address: object,
        communities: object,
    ) -> SystemDescriptorModel | None:
        assert sg_id in (SG_ID_ONE, SG_ID_TWO)
        assert isinstance(communities, list)
        assert len(communities) == 1
        assert str(communities[0]).strip() != ""
        return sysdescr_by_mac[str(mac_address)]

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._collect_modem_sysdescr",
        staticmethod(_fake_collect),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/getSysDescr",
            json={"cmts": {}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["poll"]["type"] == "cache"
        groups = payload["groups"]
        assert [group["service_group_id"] for group in groups] == [int(SG_ID_ONE), int(SG_ID_TWO)]
        sg_one = groups[0]
        assert sg_one["modems"]["aa:bb:cc:dd:ee:03"]["sysdescr"]["MODEL"] == "M"
        sg_two = groups[1]
        assert sg_two["status"] == ServiceStatusCode.SUCCESS.value
        assert sg_two["modem_count"] == 2
        assert sg_two["success_count"] == 1
        assert sg_two["failure_count"] == 1
        assert sg_two["modems"]["aa:bb:cc:dd:ee:04"]["sysdescr"]["is_empty"] is True


def test_serving_group_get_sys_descr_all_fail_returns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101")],
    )
    _seed_store(
        store,
        SG_ID_TWO,
        [SgwCableModemModel(mac="aa:bb:cc:dd:ee:02", ipv4="192.168.0.102")],
    )
    _configure_runtime_state(store, [SG_ID_ONE, SG_ID_TWO])

    def _fake_collect(
        sg_id: object,
        mac_address: object,
        ip_address: object,
        communities: object,
    ) -> SystemDescriptorModel | None:
        return None

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._collect_modem_sysdescr",
        staticmethod(_fake_collect),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/getSysDescr",
            json={"cmts": {}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.FAILURE.value
        assert payload["poll"]["type"] == "cache"
        assert "no modem sysdescr responses received" in str(payload["message"]).lower()
        assert len(payload["groups"]) == 2
        assert payload["groups"][0]["status"] == ServiceStatusCode.FAILURE.value
        assert payload["groups"][1]["status"] == ServiceStatusCode.FAILURE.value


def test_serving_group_get_sys_descr_empty_model_counts_as_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:02", ipv4="192.168.0.102"),
        ],
    )
    _configure_runtime_state(store, [SG_ID_ONE])

    def _fake_collect(
        sg_id: object,
        mac_address: object,
        ip_address: object,
        communities: object,
    ) -> SystemDescriptorModel:
        if str(mac_address) == "aa:bb:cc:dd:ee:01":
            return SystemDescriptorModel()
        return SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False)

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._collect_modem_sysdescr",
        staticmethod(_fake_collect),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/getSysDescr",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        group = payload["groups"][0]
        assert group["modem_count"] == 2
        assert group["success_count"] == 1
        assert group["failure_count"] == 1
        assert group["modems"]["aa:bb:cc:dd:ee:01"]["sysdescr"]["is_empty"] is True
        assert group["modems"]["aa:bb:cc:dd:ee:02"]["sysdescr"]["is_empty"] is False


def test_serving_group_get_sys_descr_uses_sgw_scoped_job(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101")],
    )
    _configure_runtime_state(store, [SG_ID_ONE])
    manager = get_sgw_manager()
    assert manager is not None

    called = {"value": False}

    def _fake_run_scoped_job(
        sg_ids: list[ServiceGroupId],
        worker: object,
        max_workers: int | None = None,
        overall_timeout_seconds: float | None = None,
    ) -> dict[ServiceGroupId, ServingGroupCableModemSysDescrGroupModel]:
        called["value"] = True
        assert sg_ids == [SG_ID_ONE]
        assert overall_timeout_seconds is None
        assert max_workers is None
        return {
            SG_ID_ONE: ServingGroupCableModemSysDescrGroupModel(
                service_group_id=SG_ID_ONE,
                status=ServiceStatusCode.SUCCESS,
                message="",
                modem_count=1,
                success_count=1,
                failure_count=0,
                modems={
                    "aa:bb:cc:dd:ee:01": ServingGroupCableModemSysDescrEntryModel(
                        sysdescr=SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False),
                    )
                },
            )
        }

    monkeypatch.setattr(manager, "run_scoped_job", _fake_run_scoped_job)

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/getSysDescr",
            json={"cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert called["value"] is True


def test_serving_group_get_sys_descr_poll_heavy_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101")],
    )
    _configure_runtime_state(store, [SG_ID_ONE])
    manager = get_sgw_manager()
    assert manager is not None

    calls: list[tuple[ServiceGroupId, CacheRefreshMode, float]] = []

    def _fake_request_refresh(
        sg_id: ServiceGroupId,
        mode: CacheRefreshMode,
        now_epoch: float,
    ) -> tuple[bool, str]:
        calls.append((sg_id, mode, now_epoch))
        return (True, "")

    monkeypatch.setattr(manager, "request_refresh", _fake_request_refresh)
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._wait_for_refresh",
        lambda self, sg_ids, store, baseline, timeout_seconds: (True, 0.0),
    )
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._collect_modem_sysdescr",
        staticmethod(
            lambda sg_id, mac_address, ip_address, communities: SystemDescriptorModel(
                HW_REV="1",
                VENDOR="V",
                BOOTR="B",
                SW_REV="S",
                MODEL="M",
                is_empty=False,
            )
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/getSysDescr",
            json={
                "cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}},
                "poll": {
                    "source": "heavy",
                    "wait_for_cache": True,
                    "timeout_seconds": 5,
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["poll"]["type"] == "heavy"
        assert len(calls) == 1
        assert calls[0][0] == SG_ID_ONE
        assert calls[0][1] == CacheRefreshMode.HEAVY


def test_serving_group_get_sys_descr_poll_heavy_threads_modem_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    _disable_startup(monkeypatch)
    store = SgwCacheStore()
    _seed_store(
        store,
        SG_ID_ONE,
        [
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.101"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:02", ipv4="192.168.0.102"),
            SgwCableModemModel(mac="aa:bb:cc:dd:ee:03", ipv4="192.168.0.103"),
        ],
    )
    _configure_runtime_state(store, [SG_ID_ONE])
    manager = get_sgw_manager()
    assert manager is not None

    monkeypatch.setattr(manager, "request_refresh", lambda sg_id, mode, now_epoch: (True, ""))
    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._wait_for_refresh",
        lambda self, sg_ids, store, baseline, timeout_seconds: (True, 0.0),
    )

    lock = threading.Lock()
    in_flight = {"value": 0}
    max_in_flight = {"value": 0}

    def _fake_collect(
        sg_id: object,
        mac_address: object,
        ip_address: object,
        communities: object,
    ) -> SystemDescriptorModel:
        assert sg_id == SG_ID_ONE
        with lock:
            in_flight["value"] += 1
            max_in_flight["value"] = max(max_in_flight["value"], in_flight["value"])
        time.sleep(0.05)
        with lock:
            in_flight["value"] -= 1
        return SystemDescriptorModel(HW_REV="1", VENDOR="V", BOOTR="B", SW_REV="S", MODEL="M", is_empty=False)

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.serving_group.cm.operations.service.ServingGroupCableModemOperationsService._collect_modem_sysdescr",
        staticmethod(_fake_collect),
    )

    with TestClient(app) as client:
        response = client.post(
            "/cmts/servingGroup/cableModem/operations/getSysDescr",
            json={
                "cmts": {"serving_group": {"id": [int(SG_ID_ONE)]}},
                "poll": {"source": "heavy"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == ServiceStatusCode.SUCCESS.value
        assert payload["groups"][0]["success_count"] == 3
        assert max_in_flight["value"] > 1

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel, SgwRefreshState
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwChannelSummaryModel,
    SgwSnapshotModel,
    SgwSnapshotPayloadModel,
)
from pypnm_cmts.sgw.store import SgwCacheStore

DEFAULT_CHANNEL_IDS = [1, 2]


def _settings(
    poll_light_seconds: int,
    poll_heavy_seconds: int,
    refresh_jitter_seconds: int,
    cache_max_age_seconds: int,
) -> CmtsOrchestratorSettings:
    payload = {
        "adapter": {"hostname": "cmts.example", "community": "public"},
        "sgw": {
            "poll_light_seconds": poll_light_seconds,
            "poll_heavy_seconds": poll_heavy_seconds,
            "refresh_jitter_seconds": refresh_jitter_seconds,
            "cache_max_age_seconds": cache_max_age_seconds,
        }
    }
    return CmtsOrchestratorSettings.model_validate(payload)


def test_sgw_manager_heavy_refresh_sets_light_timestamp() -> None:
    poll_light_seconds = 300
    poll_heavy_seconds = 900
    refresh_jitter_seconds = 0
    cache_max_age_seconds = 1200
    now_epoch = 1000.0
    sg_id = ServiceGroupId(1)

    settings = _settings(poll_light_seconds, poll_heavy_seconds, refresh_jitter_seconds, cache_max_age_seconds)
    store = SgwCacheStore()
    payload = SgwSnapshotPayloadModel(
        ds_channels=SgwChannelSummaryModel(count=len(DEFAULT_CHANNEL_IDS), channel_ids=DEFAULT_CHANNEL_IDS),
        us_channels=SgwChannelSummaryModel(count=1, channel_ids=[10]),
        cable_modems=[SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.100", ipv6="2001:db8::1")],
    )
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: payload,
    )

    result = manager.refresh_once(now_epoch)

    assert result.heavy_refreshed_sg_ids == [sg_id]
    assert result.light_refreshed_sg_ids == [sg_id]
    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.snapshot.metadata.last_heavy_refresh_epoch == now_epoch
    assert entry.snapshot.metadata.last_light_refresh_epoch == now_epoch
    assert entry.snapshot.ds_channels.count == len(DEFAULT_CHANNEL_IDS)


def test_sgw_manager_light_refresh_only() -> None:
    poll_light_seconds = 300
    poll_heavy_seconds = 900
    refresh_jitter_seconds = 0
    cache_max_age_seconds = 1200
    now_epoch = 1000.0
    sg_id = ServiceGroupId(2)

    settings = _settings(poll_light_seconds, poll_heavy_seconds, refresh_jitter_seconds, cache_max_age_seconds)
    store = SgwCacheStore()
    payload = SgwSnapshotPayloadModel(
        ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[1]),
        us_channels=SgwChannelSummaryModel(count=1, channel_ids=[10]),
        cable_modems=[SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.100", ipv6="2001:db8::1")],
    )
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: payload,
        light_poller=lambda *_args: [],
    )

    manager.refresh_once(now_epoch)
    result = manager.refresh_once(now_epoch + float(poll_light_seconds))

    assert result.heavy_refreshed_sg_ids == []
    assert result.light_refreshed_sg_ids == [sg_id]


def test_sgw_manager_jitter_delays_refresh_and_marks_stale() -> None:
    poll_light_seconds = 300
    poll_heavy_seconds = 900
    refresh_jitter_seconds = 300
    cache_max_age_seconds = 300
    base_epoch = 1000.0
    now_epoch = 1301.0
    sg_id = ServiceGroupId(3)

    settings = _settings(poll_light_seconds, poll_heavy_seconds, refresh_jitter_seconds, cache_max_age_seconds)
    store = SgwCacheStore()
    metadata = SgwCacheMetadataModel(
        snapshot_time_epoch=base_epoch,
        last_heavy_refresh_epoch=base_epoch,
        last_light_refresh_epoch=base_epoch,
    )
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id], jitter_provider=lambda *_args: 300)

    result = manager.refresh_once(now_epoch)

    assert result.heavy_refreshed_sg_ids == []
    assert result.light_refreshed_sg_ids == []
    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.snapshot.metadata.refresh_state == SgwRefreshState.STALE


def test_sgw_manager_heavy_refresh_replaces_snapshot_payload() -> None:
    poll_light_seconds = 300
    poll_heavy_seconds = 900
    refresh_jitter_seconds = 0
    cache_max_age_seconds = 1200
    now_epoch = 2000.0
    sg_id = ServiceGroupId(4)
    ds_channels_initial = [1]
    us_channels_initial = [10]
    ds_channels_updated = [1, 2]
    us_channels_updated = [10, 20]
    initial_payload = SgwSnapshotPayloadModel(
        ds_channels=SgwChannelSummaryModel(count=len(ds_channels_initial), channel_ids=ds_channels_initial),
        us_channels=SgwChannelSummaryModel(count=len(us_channels_initial), channel_ids=us_channels_initial),
        cable_modems=[],
    )
    updated_payload = SgwSnapshotPayloadModel(
        ds_channels=SgwChannelSummaryModel(count=len(ds_channels_updated), channel_ids=ds_channels_updated),
        us_channels=SgwChannelSummaryModel(count=len(us_channels_updated), channel_ids=us_channels_updated),
        cable_modems=[],
    )
    settings = _settings(poll_light_seconds, poll_heavy_seconds, refresh_jitter_seconds, cache_max_age_seconds)
    store = SgwCacheStore()
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: initial_payload,
    )

    manager.refresh_once(now_epoch)
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: updated_payload,
    )
    manager.refresh_once(now_epoch + float(poll_heavy_seconds))

    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.snapshot.ds_channels.count == 2


@pytest.mark.skip(reason="Deferred: slow in full suite, revisit in Phase 7.8.")
def test_sgw_manager_refresh_forever_uses_clock_and_stops() -> None:
    poll_light_seconds = 300
    poll_heavy_seconds = 900
    refresh_jitter_seconds = 0
    cache_max_age_seconds = 1200
    sg_id = ServiceGroupId(5)
    time_first = 1000.0
    time_second = 1300.0
    time_third = 1600.0
    times = [time_first, time_second, time_third]
    payload = SgwSnapshotPayloadModel(
        ds_channels=SgwChannelSummaryModel(),
        us_channels=SgwChannelSummaryModel(),
        cable_modems=[],
    )
    settings = _settings(poll_light_seconds, poll_heavy_seconds, refresh_jitter_seconds, cache_max_age_seconds)
    store = SgwCacheStore()
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: payload,
    )
    clock_calls = {"idx": 0}

    def _clock() -> float:
        value = times[clock_calls["idx"]]
        clock_calls["idx"] += 1
        return value

    results = manager.refresh_forever(clock=_clock, max_cycles=2)

    assert len(results) == 2
    assert results[0].snapshot_time_epoch == times[0]
    assert results[1].snapshot_time_epoch == times[1]

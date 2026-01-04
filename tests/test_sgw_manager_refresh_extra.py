# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwChannelSummaryModel,
    SgwSnapshotModel,
    SgwSnapshotPayloadModel,
)
from pypnm_cmts.sgw.store import SgwCacheStore

POLL_LIGHT_SECONDS = 300
POLL_HEAVY_SECONDS = 900
REFRESH_JITTER_SECONDS = 0
CACHE_MAX_AGE_SECONDS = 1200


def _settings() -> CmtsOrchestratorSettings:
    payload = {
        "sgw": {
            "enabled": True,
            "poll_light_seconds": POLL_LIGHT_SECONDS,
            "poll_heavy_seconds": POLL_HEAVY_SECONDS,
            "refresh_jitter_seconds": REFRESH_JITTER_SECONDS,
            "cache_max_age_seconds": CACHE_MAX_AGE_SECONDS,
        }
    }
    return CmtsOrchestratorSettings.model_validate(payload)


@pytest.mark.unit
def test_sgw_manager_heavy_refresh_writes_snapshot() -> None:
    now_epoch = 1_000.0
    sg_id = ServiceGroupId(10)
    payload = SgwSnapshotPayloadModel(
        ds_channels=SgwChannelSummaryModel(count=1, channel_ids=[1]),
        us_channels=SgwChannelSummaryModel(count=1, channel_ids=[10]),
        cable_modems=[SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.100")],
    )
    store = SgwCacheStore()
    manager = SgwManager(
        settings=_settings(),
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: payload,
    )

    manager.refresh_once(now_epoch)

    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.snapshot.ds_channels.count == 1
    assert entry.snapshot.us_channels.count == 1
    assert len(entry.snapshot.cable_modems) == 1
    assert entry.snapshot.metadata.snapshot_time_epoch == now_epoch
    assert entry.snapshot.metadata.last_heavy_refresh_epoch == now_epoch
    assert entry.snapshot.metadata.last_light_refresh_epoch == now_epoch


@pytest.mark.unit
def test_sgw_manager_light_refresh_updates_modems() -> None:
    base_epoch = 2_000.0
    now_epoch = base_epoch + float(POLL_LIGHT_SECONDS)
    sg_id = ServiceGroupId(11)
    initial_metadata = SgwCacheMetadataModel(
        snapshot_time_epoch=base_epoch,
        last_heavy_refresh_epoch=base_epoch,
        last_light_refresh_epoch=base_epoch,
    )
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=initial_metadata)
    store = SgwCacheStore()
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))
    updated_modems = [SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.100")]
    manager = SgwManager(
        settings=_settings(),
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        light_poller=lambda *_args: list(updated_modems),
    )

    manager.refresh_once(now_epoch)

    entry = store.get_entry(sg_id)
    assert entry is not None
    assert len(entry.snapshot.cable_modems) == 1
    assert entry.snapshot.metadata.last_light_refresh_epoch == now_epoch

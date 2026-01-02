# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel, SgwRefreshState
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import SgwCacheEntryModel
from pypnm_cmts.sgw.store import SgwCacheStore


def _settings(
    poll_light_seconds: int,
    poll_heavy_seconds: int,
    refresh_jitter_seconds: int,
    cache_max_age_seconds: int,
) -> CmtsOrchestratorSettings:
    payload = {
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
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id], jitter_provider=lambda *_args: 0)

    result = manager.refresh_once(now_epoch)

    assert result.heavy_refreshed_sg_ids == [sg_id]
    assert result.light_refreshed_sg_ids == [sg_id]
    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.metadata.last_heavy_refresh_epoch == now_epoch
    assert entry.metadata.last_light_refresh_epoch == now_epoch


def test_sgw_manager_light_refresh_only() -> None:
    poll_light_seconds = 300
    poll_heavy_seconds = 900
    refresh_jitter_seconds = 0
    cache_max_age_seconds = 1200
    now_epoch = 1000.0
    sg_id = ServiceGroupId(2)

    settings = _settings(poll_light_seconds, poll_heavy_seconds, refresh_jitter_seconds, cache_max_age_seconds)
    store = SgwCacheStore()
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id], jitter_provider=lambda *_args: 0)

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
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, metadata=metadata))
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id], jitter_provider=lambda *_args: 300)

    result = manager.refresh_once(now_epoch)

    assert result.heavy_refreshed_sg_ids == []
    assert result.light_refreshed_sg_ids == []
    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.metadata.refresh_state == SgwRefreshState.STALE

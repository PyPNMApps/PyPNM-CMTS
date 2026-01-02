# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)
from pypnm_cmts.sgw.models import SgwCacheEntryModel, SgwSnapshotModel
from pypnm_cmts.sgw.store import SgwCacheStore


def test_sgw_store_upsert_and_update_metadata() -> None:
    sg_id = ServiceGroupId(1)
    now_epoch = 1000.0
    metadata = SgwCacheMetadataModel(snapshot_time_epoch=now_epoch)
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
    entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)
    store = SgwCacheStore()

    store.upsert_entry(entry)
    assert store.get_ids() == [sg_id]
    assert store.get_entry(sg_id) == entry

    updated = SgwCacheMetadataModel(snapshot_time_epoch=now_epoch + 1.0, age_seconds=1.0)
    store.update_metadata(sg_id, updated)
    stored = store.get_entry(sg_id)
    assert stored is not None
    assert stored.snapshot.metadata.snapshot_time_epoch == now_epoch + 1.0


def test_sgw_store_update_metadata_creates_entry() -> None:
    sg_id = ServiceGroupId(2)
    now_epoch = 2000.0
    store = SgwCacheStore()
    metadata = SgwCacheMetadataModel(snapshot_time_epoch=now_epoch)

    store.update_metadata(sg_id, metadata)
    stored = store.get_entry(sg_id)
    assert stored is not None
    assert stored.snapshot.metadata.snapshot_time_epoch == now_epoch


def test_sgw_store_mark_error_bounds_message() -> None:
    sg_id = ServiceGroupId(3)
    now_epoch = 3000.0
    store = SgwCacheStore()
    message = "x" * (SGW_LAST_ERROR_MAX_LENGTH + 1)

    metadata = store.mark_error(sg_id, message, now_epoch)
    assert metadata.refresh_state == SgwRefreshState.ERROR
    assert metadata.snapshot_time_epoch == now_epoch
    assert metadata.last_error is not None
    assert len(metadata.last_error) == SGW_LAST_ERROR_MAX_LENGTH


def test_sgw_store_compute_staleness() -> None:
    cache_max_age_seconds = 300
    age_seconds = 300.0

    assert SgwCacheStore.compute_staleness(age_seconds, cache_max_age_seconds) is True


def test_sgw_store_compute_staleness_below_boundary() -> None:
    cache_max_age_seconds = 300
    age_seconds = 299.9

    assert SgwCacheStore.compute_staleness(age_seconds, cache_max_age_seconds) is False

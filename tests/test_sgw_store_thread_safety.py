# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import threading
from queue import SimpleQueue

import pytest

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.models import SgwCacheEntryModel, SgwSnapshotModel
from pypnm_cmts.sgw.store import SgwCacheStore


@pytest.mark.unit
def test_sgw_store_copy_on_read_does_not_mutate_store() -> None:
    sg_id = ServiceGroupId(1)
    store = SgwCacheStore()
    metadata = SgwCacheMetadataModel(snapshot_time_epoch=1000.0)
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
    entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)
    store.upsert_entry(entry)

    entry_copy = store.get_entry(sg_id)
    assert entry_copy is not None
    updated_metadata = entry_copy.snapshot.metadata.model_copy(update={"snapshot_time_epoch": 2000.0})
    entry_copy.snapshot = entry_copy.snapshot.model_copy(update={"metadata": updated_metadata})

    stored = store.get_entry(sg_id)
    assert stored is not None
    assert stored.snapshot.metadata.snapshot_time_epoch == 1000.0


@pytest.mark.unit
def test_sgw_store_copy_on_write_does_not_mutate_store() -> None:
    sg_id = ServiceGroupId(2)
    store = SgwCacheStore()
    metadata = SgwCacheMetadataModel(snapshot_time_epoch=1000.0)
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
    entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)
    store.upsert_entry(entry)

    updated_metadata = entry.snapshot.metadata.model_copy(update={"snapshot_time_epoch": 2000.0})
    entry.snapshot = entry.snapshot.model_copy(update={"metadata": updated_metadata})

    stored = store.get_entry(sg_id)
    assert stored is not None
    assert stored.snapshot.metadata.snapshot_time_epoch == 1000.0


@pytest.mark.unit
def test_sgw_store_thread_safety_smoke() -> None:
    store = SgwCacheStore()
    sg_id = ServiceGroupId(3)
    start_event = threading.Event()
    exceptions: SimpleQueue[BaseException] = SimpleQueue()

    def _writer() -> None:
        try:
            start_event.wait()
            for idx in range(200):
                metadata = SgwCacheMetadataModel(snapshot_time_epoch=float(idx))
                snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
                entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)
                store.upsert_entry(entry)
                store.mark_error(sg_id, "error", float(idx))
        except BaseException as exc:
            exceptions.put(exc)

    def _reader() -> None:
        try:
            start_event.wait()
            for _ in range(200):
                _ = store.get_ids()
                entry = store.get_entry(sg_id)
                if entry is not None:
                    _ = entry.snapshot.metadata.snapshot_time_epoch
        except BaseException as exc:
            exceptions.put(exc)

    writer_thread = threading.Thread(target=_writer)
    reader_thread = threading.Thread(target=_reader)
    writer_thread.start()
    reader_thread.start()
    start_event.set()
    writer_thread.join(timeout=5.0)
    reader_thread.join(timeout=5.0)

    assert not writer_thread.is_alive()
    assert not reader_thread.is_alive()
    assert exceptions.empty()

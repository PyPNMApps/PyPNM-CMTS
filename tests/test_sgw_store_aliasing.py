# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import threading
from queue import SimpleQueue

import pytest

from pypnm_cmts.api.routes.serving_group.schemas import (
    GetServingGroupCableModemsRequest,
    ServingGroupCableModemEntryModel,
)
from pypnm_cmts.api.routes.serving_group.service import ServingGroupCacheService
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwSnapshotModel,
    SgwSnapshotPayloadModel,
)
from pypnm_cmts.sgw.runtime_state import (
    reset_sgw_runtime_state,
    set_sgw_startup_success,
)
from pypnm_cmts.sgw.store import SgwCacheStore


@pytest.mark.unit
def test_service_response_mutation_does_not_alias_store() -> None:
    reset_sgw_runtime_state()
    try:
        service = ServingGroupCacheService()
        store = SgwCacheStore()
        settings = CmtsOrchestratorSettings.model_validate(
            {"adapter": {"hostname": "cmts.example", "community": "public"}}
        )
        sg_id = ServiceGroupId(1)
        metadata = SgwCacheMetadataModel(snapshot_time_epoch=1_000.0, age_seconds=0.0)
        snapshot = SgwSnapshotModel(
            sg_id=sg_id,
            metadata=metadata,
            cable_modems=[
                SgwCableModemModel(
                    mac="aa:bb:cc:dd:ee:ff",
                    ipv4="192.168.0.100",
                    ipv6="2001:db8::1",
                )
            ],
        )
        store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))
        manager = SgwManager(settings=settings, store=store, service_groups=[sg_id])
        set_sgw_startup_success([sg_id], store, manager, 1_000.0)

        request = GetServingGroupCableModemsRequest(
            cmts={"serving_group": {"id": [int(sg_id)]}},
            page=1,
            page_size=10,
        )
        response = service.get_cable_modems(request)
        response.groups[0].items.append(
            ServingGroupCableModemEntryModel(
                mac_address="aa:bb:cc:dd:ee:01",
                ipv4="192.168.0.101",
                ipv6="2001:db8::2",
            )
        )
        response.groups[0].metadata.last_error = "mutated"

        stored = store.get_entry(sg_id)
        assert stored is not None
        assert len(stored.snapshot.cable_modems) == 1
        assert stored.snapshot.metadata.last_error in ("", None)
    finally:
        reset_sgw_runtime_state()


@pytest.mark.unit
def test_concurrent_refresh_and_reads_do_not_alias_or_throw() -> None:
    reset_sgw_runtime_state()
    try:
        store = SgwCacheStore()
        settings = CmtsOrchestratorSettings.model_validate(
            {
                "adapter": {"hostname": "cmts.example", "community": "public"},
                "sgw": {
                    "poll_light_seconds": 1,
                    "poll_heavy_seconds": 1,
                    "refresh_jitter_seconds": 0,
                }
            }
        )
        sg_id = ServiceGroupId(2)
        payload = SgwSnapshotPayloadModel(
            cable_modems=[
                SgwCableModemModel(mac="aa:bb:cc:dd:ee:02", ipv4="192.168.0.111", ipv6="2001:db8::11"),
                SgwCableModemModel(mac="aa:bb:cc:dd:ee:03", ipv4="192.168.0.112", ipv6="2001:db8::12"),
            ],
        )

        def _heavy(_sg_id: ServiceGroupId, _settings: CmtsOrchestratorSettings) -> SgwSnapshotPayloadModel:
            return payload.model_copy(deep=True)

        def _light(
            _sg_id: ServiceGroupId,
            _settings: CmtsOrchestratorSettings,
            cable_modems: list[SgwCableModemModel],
        ) -> list[SgwCableModemModel]:
            return [
                SgwCableModemModel(
                    mac=modem.mac,
                    ipv4=modem.ipv4,
                    ipv6=modem.ipv6,
                )
                for modem in cable_modems
            ]

        manager = SgwManager(
            settings=settings,
            store=store,
            service_groups=[sg_id],
            jitter_provider=lambda *_args: 0,
            heavy_poller=_heavy,
            light_poller=_light,
        )
        set_sgw_startup_success([sg_id], store, manager, 1_000.0)
        service = ServingGroupCacheService()
        exceptions = SimpleQueue()

        def _writer() -> None:
            try:
                for idx in range(30):
                    manager.refresh_once(1_000.0 + float(idx))
            except BaseException as exc:
                exceptions.put(exc)

        def _reader() -> None:
            try:
                for _ in range(100):
                    store.get_ids()
                    entry = store.get_entry(sg_id)
                    if entry is not None:
                        _ = entry.snapshot.metadata.snapshot_time_epoch
                    request = GetServingGroupCableModemsRequest(
                        cmts={"serving_group": {"id": [int(sg_id)]}},
                        page=1,
                        page_size=10,
                    )
                    response = service.get_cable_modems(request)
                    assert response.resolved_sg_ids == [sg_id]
            except BaseException as exc:
                exceptions.put(exc)

        writer_thread = threading.Thread(target=_writer)
        reader_thread = threading.Thread(target=_reader)
        writer_thread.start()
        reader_thread.start()
        writer_thread.join(timeout=3.0)
        reader_thread.join(timeout=3.0)

        assert not writer_thread.is_alive()
        assert not reader_thread.is_alive()
        assert exceptions.empty()

        entry = store.get_entry(sg_id)
        assert entry is not None
        macs = [str(modem.mac) for modem in entry.snapshot.cable_modems]
        assert macs == ["aa:bb:cc:dd:ee:02", "aa:bb:cc:dd:ee:03"]
    finally:
        reset_sgw_runtime_state()

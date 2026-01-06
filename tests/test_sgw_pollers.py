# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest
from pypnm.lib.types import InetAddressStr, IPv4Str, IPv6Str, MacAddressStr

from pypnm_cmts.cmts.discovery_models import (
    RegisteredCableModemModel,
    ServiceGroupCableModemInventoryModel,
)
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.docsis.data_type.docs_if31_cmts_ds_ofdm_chan_entry import (
    DocsIf31CmtsDsOfdmChanRecord,
)
from pypnm_cmts.docsis.data_type.docs_if31_cmts_us_ofdma_chan_entry import (
    DocsIf31CmtsUsOfdmaChanRecord,
)
from pypnm_cmts.docsis.data_type.docs_if_downstream_channel_entry import (
    DocsIfDownstreamChannelEntry,
)
from pypnm_cmts.docsis.data_type.docs_if_upstream_channel_entry import (
    DocsIfUpstreamChannelEntry,
)
from pypnm_cmts.lib.types import MdCmSgId, MdDsSgId, MdUsSgId, ServiceGroupId
from pypnm_cmts.orchestrator.models import SGW_LAST_ERROR_MAX_LENGTH, SgwRefreshState
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.pollers.heavy import sgw_heavy_poller
from pypnm_cmts.sgw.store import SgwCacheStore

SG_ID = ServiceGroupId(1)
SNAPSHOT_EPOCH = 1000.0


def _build_settings() -> CmtsOrchestratorSettings:
    payload = {
        "adapter": {
            "hostname": "cmts.example",
            "community": "public",
            "write_community": "",
            "port": 161,
        }
    }
    return CmtsOrchestratorSettings.model_validate(payload)


def _fake_topology() -> list[CmtsServiceGroupTopologyModel]:
    return [
        CmtsServiceGroupTopologyModel(
            if_index=1,
            node_name="node-1",
            md_cm_sg_id=MdCmSgId(int(SG_ID)),
            md_ds_sg_id=MdDsSgId(10),
            md_us_sg_id=MdUsSgId(20),
            ds_exists=True,
            us_exists=True,
            ds_ch_set_id=1,
            us_ch_set_id=2,
            ds_channels=[100, 101],
            us_channels=[200],
        )
    ]


def _fake_modem_inventory() -> list[ServiceGroupCableModemInventoryModel]:
    modems = [
        RegisteredCableModemModel(
            mac=MacAddressStr("00:11:22:33:44:55"),
            ipv4=IPv4Str("192.168.0.100"),
            ipv6=IPv6Str(""),
        ),
        RegisteredCableModemModel(
            mac=MacAddressStr("00:11:22:33:44:56"),
            ipv4=IPv4Str("192.168.0.100"),
            ipv6=IPv6Str(""),
        ),
    ]
    return [
        ServiceGroupCableModemInventoryModel(
            sg_id=SG_ID,
            cm_count=len(modems),
            cms=modems,
        )
    ]


def test_sgw_manager_heavy_refresh_populates_store(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _build_settings()
    store = SgwCacheStore()
    manager = SgwManager(settings=settings, store=store, service_groups=[SG_ID], heavy_poller=sgw_heavy_poller)

    async def _fake_fetch_topology(*_args: object, **_kwargs: object) -> tuple[list[CmtsServiceGroupTopologyModel], InetAddressStr]:
        return (_fake_topology(), InetAddressStr("192.168.0.100"))

    async def _fake_fetch_channels(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[
        list[DocsIfDownstreamChannelEntry],
        list[DocsIfUpstreamChannelEntry],
        list[DocsIf31CmtsDsOfdmChanRecord],
        list[DocsIf31CmtsUsOfdmaChanRecord],
        InetAddressStr,
    ]:
        return ([], [], [], [], InetAddressStr("192.168.0.100"))

    async def _fake_discover(self: object, _sg_ids: list[ServiceGroupId]) -> list[ServiceGroupCableModemInventoryModel]:
        return _fake_modem_inventory()

    monkeypatch.setattr(
        "pypnm_cmts.cmts.service_group_topology_collector.CmtsTopologyCollector.fetch_service_group_topology",
        _fake_fetch_topology,
    )
    monkeypatch.setattr(
        "pypnm_cmts.cmts.channel_inventory_collector.CmtsChannelInventoryCollector.fetch_channel_inventory",
        _fake_fetch_channels,
    )
    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_registered_cms_by_sg",
        _fake_discover,
    )

    manager.refresh_once(SNAPSHOT_EPOCH)

    entry = store.get_entry(SG_ID)
    assert entry is not None
    assert entry.snapshot.ds_channels.count == 2
    assert entry.snapshot.us_channels.count == 1
    assert len(entry.snapshot.cable_modems) == 2
    assert [str(modem.mac) for modem in entry.snapshot.cable_modems] == [
        "00:11:22:33:44:55",
        "00:11:22:33:44:56",
    ]


def test_sgw_manager_heavy_refresh_error_marks_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _build_settings()
    store = SgwCacheStore()
    manager = SgwManager(settings=settings, store=store, service_groups=[SG_ID], heavy_poller=sgw_heavy_poller)

    async def _raise_topology(*_args: object, **_kwargs: object) -> tuple[list[CmtsServiceGroupTopologyModel], InetAddressStr]:
        message = "x" * (SGW_LAST_ERROR_MAX_LENGTH + 5)
        raise RuntimeError(message)

    monkeypatch.setattr(
        "pypnm_cmts.cmts.service_group_topology_collector.CmtsTopologyCollector.fetch_service_group_topology",
        _raise_topology,
    )

    manager.refresh_once(SNAPSHOT_EPOCH)

    entry = store.get_entry(SG_ID)
    assert entry is not None
    assert entry.snapshot.metadata.refresh_state == SgwRefreshState.ERROR
    assert entry.snapshot.metadata.last_error is not None
    assert len(entry.snapshot.metadata.last_error) == SGW_LAST_ERROR_MAX_LENGTH

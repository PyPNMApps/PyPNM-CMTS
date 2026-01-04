# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from pypnm.lib.types import SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.cmts.service_group_topology_collector import CmtsTopologyCollector
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwChannelSummaryModel,
    SgwSnapshotPayloadModel,
)

T = TypeVar("T")


def _run_asyncio(coro: Awaitable[T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()
    raise RuntimeError("heavy poller cannot be run from inside an existing asyncio loop")


def sgw_heavy_poller(
    sg_id: ServiceGroupId,
    settings: CmtsOrchestratorSettings,
) -> SgwSnapshotPayloadModel:
    """
    Perform a heavy refresh for a single service group.
    """
    topology = _fetch_topology(settings)
    ds_channels, us_channels = _summarize_channels(topology, sg_id)
    modems = _fetch_cable_modems(sg_id, settings)
    return SgwSnapshotPayloadModel(
        ds_channels=ds_channels,
        us_channels=us_channels,
        cable_modems=modems,
    )


def _fetch_topology(settings: CmtsOrchestratorSettings) -> list[CmtsServiceGroupTopologyModel]:
    try:
        topology, _ = _run_asyncio(
            CmtsTopologyCollector.fetch_service_group_topology(
                cmts_hostname=settings.adapter.hostname,
                read_community=settings.adapter.community,
                write_community=SnmpWriteCommunity(str(settings.adapter.write_community)),
                port=int(settings.adapter.port),
            )
        )
        return topology
    except Exception as exc:
        raise RuntimeError(f"Failed to collect service group topology: {exc}") from exc


def _fetch_cable_modems(
    sg_id: ServiceGroupId,
    settings: CmtsOrchestratorSettings,
) -> list[SgwCableModemModel]:
    service = CmtsInventoryDiscoveryService(
        cmts_hostname=settings.adapter.hostname,
        read_community=SnmpReadCommunity(str(settings.adapter.community)),
        write_community=SnmpWriteCommunity(str(settings.adapter.write_community)),
        port=int(settings.adapter.port),
    )
    try:
        per_sg = _run_asyncio(service.discover_registered_cms_by_sg([sg_id]))
    except Exception as exc:
        raise RuntimeError(f"Failed to collect cable modem membership: {exc}") from exc
    if not per_sg:
        return []
    modems = [
        SgwCableModemModel(mac=cm.mac, ipv4=cm.ipv4, ipv6=cm.ipv6)
        for cm in per_sg[0].cms
    ]
    return sorted(modems, key=lambda modem: (str(modem.mac), str(modem.ipv4), str(modem.ipv6)))


def _summarize_channels(
    topology: list[CmtsServiceGroupTopologyModel],
    sg_id: ServiceGroupId,
) -> tuple[SgwChannelSummaryModel, SgwChannelSummaryModel]:
    ds_channels: set[int] = set()
    us_channels: set[int] = set()
    for entry in topology:
        if int(entry.md_cm_sg_id) != int(sg_id):
            continue
        ds_channels.update(int(channel) for channel in entry.ds_channels)
        us_channels.update(int(channel) for channel in entry.us_channels)
    ds_list = sorted(ds_channels)
    us_list = sorted(us_channels)
    return (
        SgwChannelSummaryModel(count=len(ds_list), channel_ids=ds_list),
        SgwChannelSummaryModel(count=len(us_list), channel_ids=us_list),
    )


__all__ = [
    "sgw_heavy_poller",
]

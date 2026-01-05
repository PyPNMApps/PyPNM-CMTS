# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Iterable
from typing import Protocol, TypeVar

from pypnm.lib.types import SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.channel_inventory_collector import CmtsChannelInventoryCollector
from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.cmts.service_group_topology_collector import CmtsTopologyCollector
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.docsis.data_type.docs_if31_cmts_ds_ofdm_chan_entry import (
    DocsIf31CmtsDsOfdmChanEntry,
    DocsIf31CmtsDsOfdmChanRecord,
)
from pypnm_cmts.docsis.data_type.docs_if31_cmts_us_ofdma_chan_entry import (
    DocsIf31CmtsUsOfdmaChanEntry,
    DocsIf31CmtsUsOfdmaChanRecord,
)
from pypnm_cmts.docsis.data_type.docs_if_downstream_channel_entry import (
    DocsIfDownstreamChannelEntry,
)
from pypnm_cmts.docsis.data_type.docs_if_upstream_channel_entry import (
    DocsIfUpstreamChannelEntry,
)
from pypnm_cmts.lib.constants import RfChannelType
from pypnm_cmts.lib.types import ChSetId, ServiceGroupId
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwChannelSummaryModel,
    SgwHeavyInventoryModel,
    SgwRfChannelModel,
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


class HeavyInventoryProvider(Protocol):
    """Provider interface for heavy refresh inventory collection."""

    def fetch_inventory(
        self,
        sg_id: ServiceGroupId,
        settings: CmtsOrchestratorSettings,
    ) -> SgwHeavyInventoryModel:
        """
        Return RF channel inventory and cable modem membership.
        """


class SnmpInventoryProvider:
    """Inventory provider using CMTS SNMP discovery services."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def fetch_inventory(
        self,
        sg_id: ServiceGroupId,
        settings: CmtsOrchestratorSettings,
    ) -> SgwHeavyInventoryModel:
        try:
            topology = self._fetch_topology(settings)
            ds_channels, us_channels, ds_ch_set_id, us_ch_set_id = self._extract_channels(topology, sg_id)
            ds_sc_qam, us_sc_qam, ds_ofdm, us_ofdma = self._fetch_channel_inventory(settings)
            ds_rf_channels = _build_ds_rf_channels(ds_channels, ds_sc_qam, ds_ofdm)
            us_rf_channels = _build_us_rf_channels(us_channels, us_sc_qam, us_ofdma)
            modems = self._fetch_cable_modems(sg_id, settings)
            return SgwHeavyInventoryModel(
                ds_ch_set_id=ds_ch_set_id,
                us_ch_set_id=us_ch_set_id,
                ds_channel_ids=list(ds_channels),
                us_channel_ids=list(us_channels),
                ds_rf_channels=ds_rf_channels,
                us_rf_channels=us_rf_channels,
                cable_modems=modems,
            )
        except Exception as exc:
            raise RuntimeError(f"Heavy refresh inventory failed: {exc}") from exc

    @staticmethod
    def _extract_channels(
        topology: list[CmtsServiceGroupTopologyModel],
        sg_id: ServiceGroupId,
    ) -> tuple[list[int], list[int], ChSetId, ChSetId]:
        ds_channels: list[int] = []
        us_channels: list[int] = []
        ds_ch_set_id = ChSetId(0)
        us_ch_set_id = ChSetId(0)
        for entry in topology:
            if int(entry.md_cm_sg_id) != int(sg_id):
                continue
            ds_channels.extend(int(channel) for channel in entry.ds_channels)
            us_channels.extend(int(channel) for channel in entry.us_channels)
            ds_ch_set_id = entry.ds_ch_set_id
            us_ch_set_id = entry.us_ch_set_id
            break
        return (ds_channels, us_channels, ds_ch_set_id, us_ch_set_id)

    @staticmethod
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

    @staticmethod
    def _fetch_channel_inventory(
        settings: CmtsOrchestratorSettings,
    ) -> tuple[
        list[DocsIfDownstreamChannelEntry],
        list[DocsIfUpstreamChannelEntry],
        list[DocsIf31CmtsDsOfdmChanRecord],
        list[DocsIf31CmtsUsOfdmaChanRecord],
    ]:
        try:
            ds_sc_qam, us_sc_qam, ds_ofdm, us_ofdma, _ = _run_asyncio(
                CmtsChannelInventoryCollector.fetch_channel_inventory(
                    cmts_hostname=settings.adapter.hostname,
                    read_community=settings.adapter.community,
                    write_community=SnmpWriteCommunity(str(settings.adapter.write_community)),
                    port=int(settings.adapter.port),
                )
            )
            return (ds_sc_qam, us_sc_qam, ds_ofdm, us_ofdma)
        except Exception as exc:
            raise RuntimeError(f"Failed to collect channel inventory: {exc}") from exc

    @staticmethod
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
        return [
            SgwCableModemModel(
                mac=cm.mac,
                ipv4=cm.ipv4,
                ipv6=cm.ipv6,
                ds_channel_set=cm.ds_channel_set,
                us_channel_set=cm.us_channel_set,
                registration_status=cm.registration_status,
            )
            for cm in per_sg[0].cms
        ]


_DEFAULT_INVENTORY_PROVIDER = SnmpInventoryProvider()


def sgw_heavy_poller(
    sg_id: ServiceGroupId,
    settings: CmtsOrchestratorSettings,
    provider: HeavyInventoryProvider | None = None,
) -> SgwSnapshotPayloadModel:
    """
    Perform a heavy refresh for a single service group.
    """
    inventory_provider = provider if provider is not None else _DEFAULT_INVENTORY_PROVIDER
    inventory = inventory_provider.fetch_inventory(sg_id, settings)
    ds_channels = _normalize_channels(inventory.ds_channel_ids)
    us_channels = _normalize_channels(inventory.us_channel_ids)
    modems = _normalize_modems(inventory.cable_modems)
    ds_rf_channels = _normalize_rf_channels(inventory.ds_rf_channels, ds_channels)
    us_rf_channels = _normalize_rf_channels(inventory.us_rf_channels, us_channels)
    return SgwSnapshotPayloadModel(
        ds_ch_set_id=inventory.ds_ch_set_id,
        us_ch_set_id=inventory.us_ch_set_id,
        ds_channels=SgwChannelSummaryModel(count=len(ds_channels), channel_ids=ds_channels),
        us_channels=SgwChannelSummaryModel(count=len(us_channels), channel_ids=us_channels),
        ds_rf_channels=ds_rf_channels,
        us_rf_channels=us_rf_channels,
        cable_modems=modems,
    )


def _normalize_channels(channel_ids: Iterable[int]) -> list[int]:
    unique = {int(channel_id) for channel_id in channel_ids if int(channel_id) > 0}
    return sorted(unique)


def _normalize_modems(modems: Iterable[SgwCableModemModel]) -> list[SgwCableModemModel]:
    seen: dict[tuple[str, str, str], SgwCableModemModel] = {}
    for modem in modems:
        key = (str(modem.mac), str(modem.ipv4), str(modem.ipv6))
        if key in seen:
            continue
        seen[key] = modem.model_copy(deep=True)
    return sorted(
        seen.values(),
        key=lambda modem: (str(modem.mac), str(modem.ipv4), str(modem.ipv6)),
    )


def _normalize_rf_channels(
    channels: Iterable[SgwRfChannelModel],
    channel_ids: Iterable[int],
) -> list[SgwRfChannelModel]:
    allowed = {int(value) for value in channel_ids if int(value) > 0}
    ordered: list[SgwRfChannelModel] = []
    for channel in channels:
        channel_id = int(channel.channel_id)
        if channel_id <= 0:
            continue
        if allowed and channel_id not in allowed:
            continue
        ordered.append(channel.model_copy(deep=True))
    return sorted(
        ordered,
        key=lambda entry: (int(entry.channel_id), str(entry.channel_type)),
    )


def _build_ds_rf_channels(
    channel_ids: Iterable[int],
    sc_qam_entries: Iterable[DocsIfDownstreamChannelEntry],
    ofdm_entries: Iterable[DocsIf31CmtsDsOfdmChanRecord],
) -> list[SgwRfChannelModel]:
    sc_qam_map = {int(entry.channel_id): entry for entry in sc_qam_entries if int(entry.channel_id) > 0}
    ofdm_map = {int(entry.channel_id): entry for entry in ofdm_entries if int(entry.channel_id) > 0}
    unique = _normalize_channels(channel_ids)
    results: list[SgwRfChannelModel] = []
    for channel_id in unique:
        if channel_id in ofdm_map:
            entry = ofdm_map[channel_id].entry
            lower, upper = _calculate_ofdm_bounds(entry)
            if lower is None or upper is None:
                lower = entry.docsIf31CmtsDsOfdmChanLowerBdryFreq
                upper = entry.docsIf31CmtsDsOfdmChanUpperBdryFreq
            width = _calculate_ofdm_width(lower, upper)
            results.append(
                SgwRfChannelModel(
                    channel_id=channel_id,
                    channel_type=RfChannelType.OFDM,
                    plc_frequency_hz=entry.docsIf31CmtsDsOfdmChanPlcFreq,
                    channel_width_hz=width,
                    lower_frequency_hz=lower,
                    upper_frequency_hz=upper,
                )
            )
            continue
        sc_entry = sc_qam_map.get(channel_id)
        center = None if sc_entry is None else sc_entry.entry.docsIfDownChannelFrequency
        width = None if sc_entry is None else sc_entry.entry.docsIfDownChannelWidth
        lower, upper = _calculate_sc_qam_bounds(center, width)
        results.append(
            SgwRfChannelModel(
                channel_id=channel_id,
                channel_type=RfChannelType.SC_QAM,
                center_frequency_hz=center,
                channel_width_hz=width,
                lower_frequency_hz=lower,
                upper_frequency_hz=upper,
            )
        )
    return results


def _build_us_rf_channels(
    channel_ids: Iterable[int],
    sc_qam_entries: Iterable[DocsIfUpstreamChannelEntry],
    ofdma_entries: Iterable[DocsIf31CmtsUsOfdmaChanRecord],
) -> list[SgwRfChannelModel]:
    sc_qam_map = {int(entry.channel_id): entry for entry in sc_qam_entries if int(entry.channel_id) > 0}
    ofdma_map = {int(entry.channel_id): entry for entry in ofdma_entries if int(entry.channel_id) > 0}
    unique = _normalize_channels(channel_ids)
    results: list[SgwRfChannelModel] = []
    for channel_id in unique:
        if channel_id in ofdma_map:
            entry = ofdma_map[channel_id].entry
            lower = entry.docsIf31CmtsUsOfdmaChanLowerBdryFreq
            upper = entry.docsIf31CmtsUsOfdmaChanUpperBdryFreq
            width = _calculate_ofdma_width(lower, upper)
            start_frequency = _calculate_ofdma_start_frequency(entry, lower)
            results.append(
                SgwRfChannelModel(
                    channel_id=channel_id,
                    channel_type=RfChannelType.OFDMA,
                    start_frequency_hz=start_frequency,
                    channel_width_hz=width,
                    lower_frequency_hz=lower,
                    upper_frequency_hz=upper,
                )
            )
            continue
        sc_entry = sc_qam_map.get(channel_id)
        center = None if sc_entry is None else sc_entry.entry.docsIfUpChannelFrequency
        width = None if sc_entry is None else sc_entry.entry.docsIfUpChannelWidth
        lower, upper = _calculate_sc_qam_bounds(center, width)
        results.append(
            SgwRfChannelModel(
                channel_id=channel_id,
                channel_type=RfChannelType.SC_QAM,
                center_frequency_hz=center,
                channel_width_hz=width,
                lower_frequency_hz=lower,
                upper_frequency_hz=upper,
            )
        )
    return results


def _calculate_sc_qam_bounds(
    center_frequency_hz: int | None,
    channel_width_hz: int | None,
) -> tuple[int | None, int | None]:
    if center_frequency_hz is None or channel_width_hz is None:
        return (None, None)
    try:
        half_width = int(channel_width_hz) // 2
        center = int(center_frequency_hz)
    except (TypeError, ValueError):
        return (None, None)
    lower = center - half_width
    upper = center + half_width
    return (lower, upper)


def _calculate_ofdm_bounds(
    entry: DocsIf31CmtsDsOfdmChanEntry,
) -> tuple[int | None, int | None]:
    zero = entry.docsIf31CmtsDsOfdmChanSubcarrierZeroFreq
    first = entry.docsIf31CmtsDsOfdmChanFirstActiveSubcarrierNum
    last = entry.docsIf31CmtsDsOfdmChanLastActiveSubcarrierNum
    spacing = entry.docsIf31CmtsDsOfdmChanSubcarrierSpacing
    lower_guard = entry.docsIf31CmtsDsOfdmChanLowerGuardbandWidth
    upper_guard = entry.docsIf31CmtsDsOfdmChanUpperGuardbandWidth
    if zero is None or first is None or last is None or spacing is None:
        return (None, None)
    if lower_guard is None or upper_guard is None:
        return (None, None)
    try:
        base = int(zero)
        first_active = int(first)
        last_active = int(last)
        subcarrier_spacing = int(spacing)
        lower_guardband = int(lower_guard)
        upper_guardband = int(upper_guard)
    except (TypeError, ValueError):
        return (None, None)
    if first_active <= 0:
        return (None, None)
    lower = base - ((first_active - 1) * subcarrier_spacing) - lower_guardband
    upper = (last_active * subcarrier_spacing) + base + upper_guardband
    return (lower, upper)


def _calculate_ofdm_width(
    lower_frequency_hz: int | None,
    upper_frequency_hz: int | None,
) -> int | None:
    if lower_frequency_hz is None or upper_frequency_hz is None:
        return None
    try:
        lower = int(lower_frequency_hz)
        upper = int(upper_frequency_hz)
    except (TypeError, ValueError):
        return None
    if upper < lower:
        return None
    return upper - lower


def _calculate_ofdma_width(
    lower_frequency_hz: int | None,
    upper_frequency_hz: int | None,
) -> int | None:
    if lower_frequency_hz is None or upper_frequency_hz is None:
        return None
    try:
        lower = int(lower_frequency_hz)
        upper = int(upper_frequency_hz)
    except (TypeError, ValueError):
        return None
    if upper < lower:
        return None
    return upper - lower


def _calculate_ofdma_start_frequency(
    entry: DocsIf31CmtsUsOfdmaChanEntry,
    lower_frequency_hz: int | None,
) -> int | None:
    if lower_frequency_hz is None:
        return None
    spacing = entry.docsIf31CmtsUsOfdmaChanSubcarrierSpacing
    zero = entry.docsIf31CmtsUsOfdmaChanSubcarrierZeroFreq
    if spacing is None or zero is None:
        return None
    try:
        base = int(lower_frequency_hz)
        offset = int(zero) * int(spacing)
    except (TypeError, ValueError):
        return None
    return base + offset


__all__ = [
    "HeavyInventoryProvider",
    "SnmpInventoryProvider",
    "sgw_heavy_poller",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.lib.types import (
    HostNameStr,
    InetAddressStr,
    SnmpReadCommunity,
    SnmpWriteCommunity,
)

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
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
from pypnm_cmts.lib.cmts_hostname_resolver import resolve_cmts_inet


class CmtsChannelInventoryCollector:
    """
    Collector for CMTS channel inventory via SNMP.
    """

    @staticmethod
    async def fetch_channel_inventory(
        cmts_hostname: HostNameStr,
        read_community: SnmpReadCommunity,
        write_community: SnmpWriteCommunity,
        port: int,
    ) -> tuple[
        list[DocsIfDownstreamChannelEntry],
        list[DocsIfUpstreamChannelEntry],
        list[DocsIf31CmtsDsOfdmChanRecord],
        list[DocsIf31CmtsUsOfdmaChanRecord],
        InetAddressStr,
    ]:
        hostname_value = str(cmts_hostname).strip()
        if hostname_value == "":
            raise ValueError("CMTS hostname is required.")

        inet, resolved_ip = resolve_cmts_inet(hostname_value)
        effective_write = str(write_community).strip()
        if effective_write == "":
            effective_write = str(read_community).strip()

        operation = CmtsOperation(
            inet=inet,
            write_community=effective_write,
            port=port,
        )
        ds_sc_qam = await operation.getDocsIfDownstreamChannelEntry()
        us_sc_qam = await operation.getDocsIfUpstreamChannelEntry()
        ds_ofdm = await operation.getDocsIf31CmtsDsOfdmChanEntry()
        us_ofdma = await operation.getDocsIf31CmtsUsOfdmaChanEntry()
        return (ds_sc_qam, us_sc_qam, ds_ofdm, us_ofdma, resolved_ip)

__all__ = [
    "CmtsChannelInventoryCollector",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet
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

        inet, resolved_ip = CmtsChannelInventoryCollector._resolve_inet(hostname_value)
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

    @staticmethod
    def _resolve_inet(hostname: HostNameStr) -> tuple[Inet, InetAddressStr]:
        try:
            inet = Inet(hostname)
            return (inet, InetAddressStr(hostname))
        except ValueError as exc:
            endpoint = HostEndpoint(hostname)
            addresses = endpoint.resolve()
            if not addresses:
                raise ValueError(f"Failed to resolve hostname: {hostname}") from exc
            inet = Inet(addresses[0])
            return (inet, InetAddressStr(addresses[0]))


__all__ = [
    "CmtsChannelInventoryCollector",
]

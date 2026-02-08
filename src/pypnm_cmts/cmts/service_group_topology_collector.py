# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm.lib.types import (
    HostNameStr,
    InetAddressStr,
    SnmpReadCommunity,
    SnmpWriteCommunity,
)

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.lib.cmts_hostname_resolver import resolve_cmts_inet


class CmtsTopologyCollector:
    """
    Collector for CMTS service-group topology via SNMP.
    """

    @staticmethod
    async def fetch_service_group_topology(
        cmts_hostname: HostNameStr,
        read_community: SnmpReadCommunity,
        write_community: SnmpWriteCommunity,
        port: int,
    ) -> tuple[list[CmtsServiceGroupTopologyModel], InetAddressStr]:
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
        topology = await operation.getServiceGroupTopology()
        return (topology, resolved_ip)

__all__ = [
    "CmtsTopologyCollector",
]

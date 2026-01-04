# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

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
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)


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

        inet, resolved_ip = CmtsTopologyCollector._resolve_inet(hostname_value)
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
    "CmtsTopologyCollector",
]

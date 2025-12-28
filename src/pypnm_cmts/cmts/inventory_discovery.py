# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet
from pypnm.lib.types import (
    HostNameStr,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    SnmpReadCommunity,
    SnmpWriteCommunity,
)
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.cmts.discovery_models import (
    InventoryDiscoveryResultModel,
    RegisteredCableModemModel,
    ServiceGroupCableModemInventoryModel,
)
from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.types import (
    CoordinationPath,
    IPv6LinkLocalStr,
    MdCmSgId,
    RegisterCmMacInetAddress,
    ServiceGroupId,
)

DEFAULT_READ_COMMUNITY: SnmpReadCommunity = SnmpReadCommunity("public")
DEFAULT_WRITE_COMMUNITY: SnmpWriteCommunity = SnmpWriteCommunity("")
DEFAULT_SNMP_PORT = Snmp_v2c.SNMP_PORT


class CmtsInventoryDiscoveryService:
    """
    Service for discovering CMTS service groups and registered cable modems via SNMP.
    """

    def __init__(
        self,
        cmts_hostname: HostNameStr,
        read_community: SnmpReadCommunity = DEFAULT_READ_COMMUNITY,
        write_community: SnmpWriteCommunity = DEFAULT_WRITE_COMMUNITY,
        port: int = DEFAULT_SNMP_PORT,
    ) -> None:
        """
        Initialize the discovery service.

        Args:
            cmts_hostname (HostNameStr): CMTS hostname or IP address.
            read_community (SnmpReadCommunity): SNMPv2c read community string.
            write_community (SnmpWriteCommunity): SNMPv2c write community string.
            port (int): SNMP port for CMTS discovery.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cmts_hostname = HostNameStr(str(cmts_hostname))
        self._read_community = SnmpReadCommunity(str(read_community))
        self._write_community = SnmpWriteCommunity(str(write_community))
        self._port = int(port)

    async def discover_inventory(
        self,
        state_dir: CoordinationPath | None = None,
    ) -> InventoryDiscoveryResultModel:
        """
        Discover service groups and registered cable modems from the CMTS.

        Args:
            state_dir (CoordinationPath | None): Optional state directory for persistence.

        Returns:
            InventoryDiscoveryResultModel: Discovered inventory grouped by service group.
        """
        service_groups = await self.discover_service_groups()
        sg_ids = [ServiceGroupId(int(entry.md_cm_sg_id)) for entry in service_groups]
        sorted_sg_ids = sorted(sg_ids, key=int)
        per_sg = await self.discover_registered_cms_by_sg(sorted_sg_ids)

        result = InventoryDiscoveryResultModel(
            cmts_host=self._cmts_hostname,
            discovered_sg_ids=sorted_sg_ids,
            per_sg=per_sg,
        )

        if state_dir is not None:
            self._persist_snapshot(result, state_dir)

        return result

    async def discover_service_groups(self) -> list[CmtsServiceGroupModel]:
        """
        Discover service group inventory from the CMTS.

        Returns:
            list[CmtsServiceGroupModel]: Discovered service group entries.
        """
        operation = self._build_operation()
        try:
            return await operation.listServiceGroups()
        except Exception as exc:
            raise RuntimeError(f"Failed to discover service groups: {exc}") from exc

    async def discover_registered_cms_by_sg(
        self,
        sg_ids: list[ServiceGroupId],
    ) -> list[ServiceGroupCableModemInventoryModel]:
        """
        Discover registered cable modems for each service group.

        Args:
            sg_ids (list[ServiceGroupId]): Service group identifiers to query.

        Returns:
            list[ServiceGroupCableModemInventoryModel]: Cable modem inventory grouped by service group.
        """
        operation = self._build_operation()
        results: list[ServiceGroupCableModemInventoryModel] = []

        for sg_id in sorted(sg_ids, key=int):
            cm_entries = await self._fetch_registered_cms(operation, sg_id)
            sorted_entries = sorted(cm_entries, key=lambda entry: str(entry.mac).lower())
            results.append(
                ServiceGroupCableModemInventoryModel(
                    sg_id=sg_id,
                    cm_count=len(sorted_entries),
                    cms=sorted_entries,
                )
            )

        return results

    @staticmethod
    def run_discovery(
        cmts_hostname: HostNameStr,
        read_community: SnmpReadCommunity,
        write_community: SnmpWriteCommunity,
        port: int,
        state_dir: CoordinationPath | None = None,
    ) -> InventoryDiscoveryResultModel:
        """
        Run discovery using a synchronous helper for CLI paths.

        Args:
            cmts_hostname (HostNameStr): CMTS hostname or IP address.
            read_community (SnmpReadCommunity): SNMPv2c read community string.
            write_community (SnmpWriteCommunity): SNMPv2c write community string.
            port (int): SNMP port for CMTS discovery.
            state_dir (CoordinationPath | None): Optional state directory for persistence.

        Returns:
            InventoryDiscoveryResultModel: Discovered inventory grouped by service group.
        """
        service = CmtsInventoryDiscoveryService(
            cmts_hostname=cmts_hostname,
            read_community=read_community,
            write_community=write_community,
            port=port,
        )
        return asyncio.run(service.discover_inventory(state_dir=state_dir))

    def _build_operation(self) -> CmtsOperation:
        """
        Build a CmtsOperation instance for SNMP operations.
        """
        hostname_value = str(self._cmts_hostname).strip()
        if hostname_value == "":
            raise ValueError("cmts_hostname must be non-empty.")

        try:
            inet = Inet(hostname_value)
        except ValueError as exc:
            endpoint = HostEndpoint(hostname_value)
            addresses = endpoint.resolve()
            if not addresses:
                raise ValueError(
                    f"Failed to resolve CMTS hostname: {hostname_value}"
                ) from exc
            inet = Inet(addresses[0])

        effective_write = str(self._write_community).strip()
        if effective_write == "":
            effective_write = str(self._read_community)

        return CmtsOperation(
            inet=inet,
            write_community=effective_write,
            port=self._port,
        )

    async def _fetch_registered_cms(
        self,
        operation: CmtsOperation,
        sg_id: ServiceGroupId,
    ) -> list[RegisteredCableModemModel]:
        """
        Fetch registered cable modems for a single service group.
        """
        try:
            entries = await operation.getAllRegisterCmMacInetAddress(
                MdCmSgId(int(sg_id))
            )
        except Exception as exc:
            self.logger.error(f"Failed to fetch registered CMs for sg_id {int(sg_id)}: {exc}")
            return []

        return [self._map_register_cm(entry) for entry in entries]

    @staticmethod
    def _map_register_cm(entry: RegisterCmMacInetAddress) -> RegisteredCableModemModel:
        """
        Map a registered CM tuple into a discovery model.
        """
        _, mac, ipv4, ipv6, ipv6_ll = entry
        return RegisteredCableModemModel(
            mac=MacAddressStr(str(mac)),
            ipv4=IPv4Str(str(ipv4)),
            ipv6=IPv6Str(str(ipv6)),
            ipv6_link_local=IPv6LinkLocalStr(IPv6Str(str(ipv6_ll))),
        )

    def _persist_snapshot(
        self,
        result: InventoryDiscoveryResultModel,
        state_dir: CoordinationPath,
    ) -> None:
        """
        Persist a discovery snapshot to the state directory.
        """
        try:
            state_path = Path(state_dir)
            inventory_dir = state_path / "inventory"
            inventory_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = inventory_dir / "discovery.json"
            snapshot_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"Failed to persist discovery snapshot: {exc}")


__all__ = [
    "CmtsInventoryDiscoveryService",
    "InventoryDiscoveryResultModel",
]

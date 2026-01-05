# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Iterable
from typing import Protocol, TypeVar

from pypnm.lib.types import SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.types import ServiceGroupId

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
    raise RuntimeError("SNMP discovery cannot run inside an existing asyncio loop")


class ServiceGroupDiscovery(Protocol):
    """Contract for discovery providers that return service group identifiers."""

    def discover(self, settings: CmtsOrchestratorSettings) -> list[ServiceGroupId]:
        """
        Discover service groups for the provided settings.

        Returns:
            list[ServiceGroupId]: Sorted, deduped list of service group identifiers.

        Raises:
            Exception: Raised when discovery fails and startup should report an error.
        """


class StaticServiceGroupDiscovery:
    """Static discovery provider backed by configured service groups."""

    def discover(self, settings: CmtsOrchestratorSettings) -> list[ServiceGroupId]:
        """
        Return service groups from configuration in sorted, deduped order.

        Returns:
            list[ServiceGroupId]: Sorted service group identifiers.
        """
        enabled_ids = self._enabled_service_groups(settings.service_groups)
        unique = {int(sg_id): sg_id for sg_id in enabled_ids}
        return [unique[key] for key in sorted(unique.keys())]

    @staticmethod
    def _enabled_service_groups(
        service_groups: Iterable[object],
    ) -> list[ServiceGroupId]:
        result: list[ServiceGroupId] = []
        for entry in service_groups:
            enabled = getattr(entry, "enabled", True)
            sg_id = getattr(entry, "sg_id", None)
            if sg_id is None or not bool(enabled):
                continue
            result.append(sg_id)
        return result


class SnmpServiceGroupDiscovery:
    """SNMP-based discovery provider that queries CMTS service groups via PyPNM."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def discover(self, settings: CmtsOrchestratorSettings) -> list[ServiceGroupId]:
        """
        Discover service groups via SNMP and return sorted, deduped identifiers.

        Returns:
            list[ServiceGroupId]: Sorted service group identifiers.
        """
        hostname_value = str(settings.adapter.hostname).strip()
        if hostname_value == "":
            raise ValueError("adapter.hostname must be set for snmp discovery.")
        community_value = str(settings.adapter.community).strip()
        if community_value == "":
            raise ValueError("adapter.community must be set for snmp discovery.")
        service_groups = self._discover_service_groups(settings)
        sg_ids = [ServiceGroupId(int(entry.md_cm_sg_id)) for entry in service_groups]
        unique = {int(sg_id): sg_id for sg_id in sg_ids}
        ordered = [unique[key] for key in sorted(unique.keys())]
        if not ordered:
            self.logger.info("SNMP discovery returned no service groups.")
        return ordered

    def _discover_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
    ) -> list[CmtsServiceGroupModel]:
        try:
            service = CmtsInventoryDiscoveryService(
                cmts_hostname=settings.adapter.hostname,
                read_community=SnmpReadCommunity(str(settings.adapter.community)),
                write_community=SnmpWriteCommunity(str(settings.adapter.write_community)),
                port=int(settings.adapter.port),
            )
            return _run_asyncio(service.discover_service_groups())
        except Exception as exc:
            raise RuntimeError(f"SNMP discovery failed: {exc}") from exc


__all__ = [
    "ServiceGroupDiscovery",
    "StaticServiceGroupDiscovery",
    "SnmpServiceGroupDiscovery",
]

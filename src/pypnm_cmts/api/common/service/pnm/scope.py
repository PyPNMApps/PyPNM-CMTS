# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from collections.abc import Callable

from pypnm.lib.types import MacAddressStr

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel
from pypnm_cmts.sgw.store import SgwCacheStore

RuntimeStoreLoader = Callable[[], SgwCacheStore | None]


class PnmOperationScopeResolver:
    """Resolve SG and modem scope for PNM operations using SGW cache state."""

    def __init__(
        self,
        sgw_store: SgwCacheStore | None = None,
        runtime_store_loader: RuntimeStoreLoader | None = None,
    ) -> None:
        self._sgw_store = sgw_store
        self._runtime_store_loader = runtime_store_loader

    def get_store(self) -> SgwCacheStore | None:
        """Return the active SGW store reference."""
        return self._sgw_store

    def resolve_modem_scope(
        self,
        requested_sg_ids: list[ServiceGroupId],
        requested_mac_addresses: list[MacAddressStr],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        """Expand wildcard SG and MAC selections using SGW inventory."""
        if requested_sg_ids and requested_mac_addresses:
            return requested_sg_ids, requested_mac_addresses

        store = self._resolve_store()
        if store is None:
            return requested_sg_ids, requested_mac_addresses

        sg_ids = requested_sg_ids if requested_sg_ids else store.get_ids()
        if not sg_ids:
            return ([], [])

        cache_entries = self._load_cache_entries(sg_ids)
        if requested_mac_addresses:
            return self._expand_macs_with_wildcard_sg(requested_mac_addresses, cache_entries)
        return self._expand_modems_for_sgs(cache_entries)

    def _resolve_store(self) -> SgwCacheStore | None:
        if self._sgw_store is not None:
            return self._sgw_store
        if self._runtime_store_loader is None:
            return None
        store = self._runtime_store_loader()
        if store is not None:
            self._sgw_store = store
        return store

    def _load_cache_entries(
        self,
        sg_ids: list[ServiceGroupId],
    ) -> list[tuple[ServiceGroupId, list[SgwCableModemModel]]]:
        entries: list[tuple[ServiceGroupId, list[SgwCableModemModel]]] = []
        store = self._sgw_store
        if store is None:
            return entries
        for sg_id in sg_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                continue
            entries.append((sg_id, list(entry.snapshot.cable_modems)))
        return entries

    @staticmethod
    def _expand_macs_with_wildcard_sg(
        requested_mac_addresses: list[MacAddressStr],
        cache_entries: list[tuple[ServiceGroupId, list[SgwCableModemModel]]],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        mac_to_sg_ids: dict[MacAddressStr, list[ServiceGroupId]] = {}
        for sg_id, cable_modems in cache_entries:
            for cable_modem in cable_modems:
                if cable_modem.mac not in mac_to_sg_ids:
                    mac_to_sg_ids[cable_modem.mac] = []
                mac_to_sg_ids[cable_modem.mac].append(sg_id)

        expanded_sg_ids: list[ServiceGroupId] = []
        expanded_mac_addresses: list[MacAddressStr] = []
        for mac_address in requested_mac_addresses:
            sg_ids = mac_to_sg_ids.get(mac_address)
            if sg_ids is None:
                continue
            for sg_id in sg_ids:
                expanded_sg_ids.append(sg_id)
                expanded_mac_addresses.append(mac_address)
        return (expanded_sg_ids, expanded_mac_addresses)

    @staticmethod
    def _expand_modems_for_sgs(
        cache_entries: list[tuple[ServiceGroupId, list[SgwCableModemModel]]],
    ) -> tuple[list[ServiceGroupId], list[MacAddressStr]]:
        expanded_sg_ids: list[ServiceGroupId] = []
        expanded_mac_addresses: list[MacAddressStr] = []
        for sg_id, cable_modems in cache_entries:
            for cable_modem in cable_modems:
                expanded_sg_ids.append(sg_id)
                expanded_mac_addresses.append(cable_modem.mac)
        return (expanded_sg_ids, expanded_mac_addresses)


__all__ = [
    "PnmOperationScopeResolver",
]


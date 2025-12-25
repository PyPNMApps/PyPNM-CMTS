# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

from pydantic import BaseModel
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import IPv4Str, IPv6Str
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.lib.types import (
    ChSetId,
    CmtsCmRegState,
    CmtsCmRegStatusId,
    DateAndTime,
    DocsisQosVersion,
    EnergyMgtBits,
    InterfaceIndexOrZero,
    MdCmSgId,
    RcpId,
)


class DocsIf3CmtsCmRegStatusEntry(BaseModel):
    """
    DOCSIS 3.1 CMTS CM registration status attributes (docsIf3CmtsCmRegStatusTable).

    Notes
    -----
    - All values are retrieved via symbolic OIDs (no compiled OIDs).
    - Presence of fields depends on device/MIB support.
    """
    docsIf3CmtsCmRegStatusId:                 CmtsCmRegStatusId = CmtsCmRegStatusId(0)
    docsIf3CmtsCmRegStatusMacAddr:            str | None = None
    docsIf3CmtsCmRegStatusIPv6Addr:           IPv6Str | None = None
    docsIf3CmtsCmRegStatusIPv6LinkLocal:      IPv6Str | None = None
    docsIf3CmtsCmRegStatusIPv4Addr:           IPv4Str | None = None
    docsIf3CmtsCmRegStatusValue:              CmtsCmRegState | None = None
    docsIf3CmtsCmRegStatusMdIfIndex:          InterfaceIndexOrZero | None = None
    docsIf3CmtsCmRegStatusMdCmSgId:           MdCmSgId | None = None
    docsIf3CmtsCmRegStatusRcpId:              RcpId | None = None
    docsIf3CmtsCmRegStatusRccStatusId:        int | None = None
    docsIf3CmtsCmRegStatusRcsId:              ChSetId | None = None
    docsIf3CmtsCmRegStatusTcsId:              ChSetId | None = None
    docsIf3CmtsCmRegStatusQosVersion:         DocsisQosVersion | None = None
    docsIf3CmtsCmRegStatusLastRegTime:        DateAndTime | None = None
    docsIf3CmtsCmRegStatusAddrResolutionReqs: int | None = None
    docsIf3CmtsCmRegStatusEnergyMgtEnabled:   EnergyMgtBits | None = None
    docsIf3CmtsCmRegStatusEnergyMgtOperStatus: EnergyMgtBits | None = None


class DocsIf3CmtsCmRegStatusIdEntry(BaseModel):
    """
    Container for a single CM registration status record retrieved via SNMP.

    Attributes
    ----------
    index : int
        Table index used to query SNMP (instance suffix).
    status_id : int
        Mirrored from ``docsIf3CmtsCmRegStatusId``; 0 if absent.
    entry : DocsIf3CmtsCmRegStatusEntry
        Populated registration status attributes for this index.
    """
    index: int
    status_id: int
    entry: DocsIf3CmtsCmRegStatusEntry

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsIf3CmtsCmRegStatusIdEntry:
        logger = logging.getLogger(cls.__name__)
        int_like_casts = (
            int,
            ChSetId,
            CmtsCmRegState,
            DocsisQosVersion,
            EnergyMgtBits,
            InterfaceIndexOrZero,
            MdCmSgId,
        )

        def safe_cast(value: str, cast: Callable) -> int | float | str | bool | None:
            try:
                if cast in int_like_casts:
                    return cast(int(value, 0))
                return cast(value)
            except Exception:
                return None

        def cast_mac(value: str) -> str | None:
            try:
                return str(MacAddress(value))
            except (TypeError, ValueError):
                return None

        async def fetch(field: str, cast: Callable | None = None) -> None | int | float | str | bool:
            try:
                raw = await snmp.get(f"{field}.{index}")
                val = Snmp_v2c.get_result_value(raw)

                if val is None or val == "":
                    return None

                if cast is not None:
                    return safe_cast(str(val), cast)

                s = str(val).strip()
                if s.isdigit():
                    return int(s)
                if s.lower() in ("true", "false"):
                    return s.lower() == "true"
                try:
                    return float(s)
                except ValueError:
                    return s
            except Exception as exc:
                logger.warning(f"Failed to fetch {field}.{index}: {exc}")
                return None

        entry = DocsIf3CmtsCmRegStatusEntry(
            docsIf3CmtsCmRegStatusId                 = CmtsCmRegStatusId(index),
            docsIf3CmtsCmRegStatusMacAddr            = await fetch("docsIf3CmtsCmRegStatusMacAddr", cast_mac),
            docsIf3CmtsCmRegStatusIPv6Addr           = await fetch("docsIf3CmtsCmRegStatusIPv6Addr", IPv6Str),
            docsIf3CmtsCmRegStatusIPv6LinkLocal      = await fetch("docsIf3CmtsCmRegStatusIPv6LinkLocal", IPv6Str),
            docsIf3CmtsCmRegStatusIPv4Addr           = await fetch("docsIf3CmtsCmRegStatusIPv4Addr", IPv4Str),
            docsIf3CmtsCmRegStatusValue              = await fetch("docsIf3CmtsCmRegStatusValue", CmtsCmRegState),
            docsIf3CmtsCmRegStatusMdIfIndex          = await fetch("docsIf3CmtsCmRegStatusMdIfIndex", InterfaceIndexOrZero),
            docsIf3CmtsCmRegStatusMdCmSgId           = await fetch("docsIf3CmtsCmRegStatusMdCmSgId", MdCmSgId),
            docsIf3CmtsCmRegStatusRcpId              = await fetch("docsIf3CmtsCmRegStatusRcpId", RcpId),
            docsIf3CmtsCmRegStatusRccStatusId        = await fetch("docsIf3CmtsCmRegStatusRccStatusId", int),
            docsIf3CmtsCmRegStatusRcsId              = await fetch("docsIf3CmtsCmRegStatusRcsId", ChSetId),
            docsIf3CmtsCmRegStatusTcsId              = await fetch("docsIf3CmtsCmRegStatusTcsId", ChSetId),
            docsIf3CmtsCmRegStatusQosVersion         = await fetch("docsIf3CmtsCmRegStatusQosVersion", DocsisQosVersion),
            docsIf3CmtsCmRegStatusLastRegTime        = await fetch("docsIf3CmtsCmRegStatusLastRegTime", DateAndTime),
            docsIf3CmtsCmRegStatusAddrResolutionReqs = await fetch("docsIf3CmtsCmRegStatusAddrResolutionReqs", int),
            docsIf3CmtsCmRegStatusEnergyMgtEnabled   = await fetch("docsIf3CmtsCmRegStatusEnergyMgtEnabled", EnergyMgtBits),
            docsIf3CmtsCmRegStatusEnergyMgtOperStatus = await fetch("docsIf3CmtsCmRegStatusEnergyMgtOperStatus", EnergyMgtBits),
        )

        return cls(
            index      = index,
            status_id  = int(entry.docsIf3CmtsCmRegStatusId or 0),
            entry      = entry
        )

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: list[int]) -> list[DocsIf3CmtsCmRegStatusIdEntry]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsIf3CmtsCmRegStatusIdEntry] = []

        if not indices:
            logger.warning("No CM registration status indices provided.")
            return results

        for i in indices:
            entry = await cls.from_snmp(i, snmp)
            if entry.entry.docsIf3CmtsCmRegStatusId != CmtsCmRegStatusId(0):
                results.append(entry)
            else:
                logger.warning(f"Failed to retrieve CM registration status {i}: invalid status ID")

        return results

    @classmethod
    async def get_entries(cls, snmp: Snmp_v2c, indices: list[int]) -> list[DocsIf3CmtsCmRegStatusEntry]:
        """
        Convenience wrapper that returns only the `DocsIf3CmtsCmRegStatusEntry`
        objects (no status wrapper), preserving a return type of
        `List[DocsIf3CmtsCmRegStatusEntry]`.
        """
        wrappers = await cls.get(snmp, indices)
        return [w.entry for w in wrappers]

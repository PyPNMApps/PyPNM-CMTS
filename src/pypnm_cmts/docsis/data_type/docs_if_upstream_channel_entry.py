# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

from pydantic import BaseModel
from pypnm.snmp.snmp_v2c import Snmp_v2c


class DocsIfUpstreamEntry(BaseModel):
    docsIfUpChannelId: int | None = None
    docsIfUpChannelFrequency: int | None = None
    docsIfUpChannelWidth: int | None = None
    docsIfUpChannelModulationProfile: int | None = None
    docsIfUpChannelSlotSize: int | None = None
    docsIfUpChannelTxTimingOffset: int | None = None
    docsIfUpChannelRangingBackoffStart: int | None = None
    docsIfUpChannelRangingBackoffEnd: int | None = None
    docsIfUpChannelTxBackoffStart: int | None = None
    docsIfUpChannelTxBackoffEnd: int | None = None
    docsIfUpChannelScdmaActiveCodes: int | None = None
    docsIfUpChannelScdmaCodesPerSlot: int | None = None
    docsIfUpChannelScdmaFrameSize: int | None = None
    docsIfUpChannelScdmaHoppingSeed: int | None = None
    docsIfUpChannelType: int | None = None
    docsIfUpChannelCloneFrom: int | None = None
    docsIfUpChannelUpdate: bool | None = None
    docsIfUpChannelStatus: int | None = None
    docsIfUpChannelPreEqEnable: bool | None = None


class DocsIfUpstreamChannelEntry(BaseModel):
    index: int
    channel_id: int
    entry: DocsIfUpstreamEntry

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsIfUpstreamChannelEntry | None:
        logger = logging.getLogger(cls.__name__)

        def safe_cast(value: str, cast: Callable) -> int | float | str | bool | None:
            try:
                return cast(value)
            except Exception:
                return None

        async def fetch(field: str, cast: Callable | None = None) -> None | int | float | str | bool:
            try:
                raw = await snmp.get(f"{field}.{index}")
                val = Snmp_v2c.get_result_value(raw)
                if val is None or val == "":
                    return None
                if cast:
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

        entry = DocsIfUpstreamEntry(
            docsIfUpChannelId                   =   await fetch("docsIfUpChannelId", int),
            docsIfUpChannelFrequency            =   await fetch("docsIfUpChannelFrequency", int),
            docsIfUpChannelWidth                =   await fetch("docsIfUpChannelWidth", int),
            docsIfUpChannelModulationProfile    =   await fetch("docsIfUpChannelModulationProfile", int),
            docsIfUpChannelSlotSize             =   await fetch("docsIfUpChannelSlotSize", int),
            docsIfUpChannelTxTimingOffset       =   await fetch("docsIfUpChannelTxTimingOffset", int),
            docsIfUpChannelRangingBackoffStart  =   await fetch("docsIfUpChannelRangingBackoffStart", int),
            docsIfUpChannelRangingBackoffEnd    =   await fetch("docsIfUpChannelRangingBackoffEnd", int),
            docsIfUpChannelTxBackoffStart       =   await fetch("docsIfUpChannelTxBackoffStart", int),
            docsIfUpChannelTxBackoffEnd         =   await fetch("docsIfUpChannelTxBackoffEnd", int),
            docsIfUpChannelScdmaActiveCodes     =   await fetch("docsIfUpChannelScdmaActiveCodes", int),
            docsIfUpChannelScdmaCodesPerSlot    =   await fetch("docsIfUpChannelScdmaCodesPerSlot", int),
            docsIfUpChannelScdmaFrameSize       =   await fetch("docsIfUpChannelScdmaFrameSize", int),
            docsIfUpChannelScdmaHoppingSeed     =   await fetch("docsIfUpChannelScdmaHoppingSeed", int),
            docsIfUpChannelType                 =   await fetch("docsIfUpChannelType", int),
            docsIfUpChannelCloneFrom            =   await fetch("docsIfUpChannelCloneFrom", int),
            docsIfUpChannelUpdate               =   await fetch("docsIfUpChannelUpdate", Snmp_v2c.truth_value),
            docsIfUpChannelStatus               =   await fetch("docsIfUpChannelStatus", int),
            docsIfUpChannelPreEqEnable          =   await fetch("docsIfUpChannelPreEqEnable", Snmp_v2c.truth_value),
        )

        return cls(
            index=index,
            channel_id=int(entry.docsIfUpChannelId or 0),
            entry=entry,
        )

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: list[int]) -> list[DocsIfUpstreamChannelEntry]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsIfUpstreamChannelEntry] = []

        if not indices:
            logger.warning("No upstream channel indices found.")
            return results

        for index in indices:
            result = await cls.from_snmp(index, snmp)
            if result is not None:
                results.append(result)

        return results

    @classmethod
    async def get_all(cls, snmp: Snmp_v2c) -> list[DocsIfUpstreamChannelEntry]:
        logger = logging.getLogger(cls.__name__)
        try:
            results = await snmp.walk("docsIfUpChannelId")
        except Exception as exc:
            logger.warning(f"SNMP walk failed for docsIfUpChannelId: {exc}")
            return []

        if not results:
            logger.warning("No upstream channel indices found.")
            return []

        indices_raw = Snmp_v2c.extract_last_oid_index(results)
        indices: list[int] = []
        for value in indices_raw:
            if not isinstance(value, (int, str)):
                continue
            try:
                indices.append(int(value))
            except (TypeError, ValueError):
                continue

        return await cls.get(snmp, indices)


__all__ = [
    "DocsIfUpstreamChannelEntry",
    "DocsIfUpstreamEntry",
]

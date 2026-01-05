# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

from pydantic import BaseModel
from pypnm.snmp.snmp_v2c import Snmp_v2c


class DocsIfDownstreamEntry(BaseModel):
    docsIfDownChannelId: int | None = None
    docsIfDownChannelFrequency: int | None = None
    docsIfDownChannelWidth: int | None = None
    docsIfDownChannelModulation: int | None = None
    docsIfDownChannelInterleave: int | None = None
    docsIfDownChannelPower: float | None = None
    docsIfDownChannelAnnex: int | None = None
    docsIfDownChannelStorageType: int | None = None


class DocsIfDownstreamChannelEntry(BaseModel):
    index: int
    channel_id: int
    entry: DocsIfDownstreamEntry

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsIfDownstreamChannelEntry | None:
        logger = logging.getLogger(cls.__name__)

        def tenthdBmV_to_float(value: str) -> float | None:
            try:
                return float(value) / 10.0
            except Exception:
                return None

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

        entry = DocsIfDownstreamEntry(
            docsIfDownChannelId           =   await fetch("docsIfDownChannelId", int),
            docsIfDownChannelFrequency    =   await fetch("docsIfDownChannelFrequency", int),
            docsIfDownChannelWidth        =   await fetch("docsIfDownChannelWidth", int),
            docsIfDownChannelModulation   =   await fetch("docsIfDownChannelModulation", int),
            docsIfDownChannelInterleave   =   await fetch("docsIfDownChannelInterleave", int),
            docsIfDownChannelPower        =   await fetch("docsIfDownChannelPower", tenthdBmV_to_float),
            docsIfDownChannelAnnex        =   await fetch("docsIfDownChannelAnnex", int),
            docsIfDownChannelStorageType  =   await fetch("docsIfDownChannelStorageType", int),
        )

        return cls(
            index=index,
            channel_id=int(entry.docsIfDownChannelId or 0),
            entry=entry,
        )

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: list[int]) -> list[DocsIfDownstreamChannelEntry]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsIfDownstreamChannelEntry] = []

        if not indices:
            logger.warning("No downstream channel indices found.")
            return results

        for index in indices:
            result = await cls.from_snmp(index, snmp)
            if result is not None:
                results.append(result)

        return results

    @classmethod
    async def get_all(cls, snmp: Snmp_v2c) -> list[DocsIfDownstreamChannelEntry]:
        logger = logging.getLogger(cls.__name__)
        try:
            results = await snmp.walk("docsIfDownChannelId")
        except Exception as exc:
            logger.warning(f"SNMP walk failed for docsIfDownChannelId: {exc}")
            return []

        if not results:
            logger.warning("No downstream channel indices found.")
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
    "DocsIfDownstreamChannelEntry",
    "DocsIfDownstreamEntry",
]

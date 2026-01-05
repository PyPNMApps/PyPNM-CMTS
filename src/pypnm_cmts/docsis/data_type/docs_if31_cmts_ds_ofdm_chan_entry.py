# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

from pydantic import BaseModel
from pypnm.snmp.snmp_v2c import Snmp_v2c


class DocsIf31CmtsDsOfdmChanEntry(BaseModel):
    docsIf31CmtsDsOfdmChanChannelId: int | None = None
    docsIf31CmtsDsOfdmChanLowerBdryFreq: int | None = None
    docsIf31CmtsDsOfdmChanUpperBdryFreq: int | None = None
    docsIf31CmtsDsOfdmChanLowerBdryEncompSpectrum: int | None = None
    docsIf31CmtsDsOfdmChanUpperBdryEncompSpectrum: int | None = None
    docsIf31CmtsDsOfdmChanPlcFreq: int | None = None
    docsIf31CmtsDsOfdmChanSubcarrierZeroFreq: int | None = None
    docsIf31CmtsDsOfdmChanFirstActiveSubcarrierNum: int | None = None
    docsIf31CmtsDsOfdmChanLastActiveSubcarrierNum: int | None = None
    docsIf31CmtsDsOfdmChanNumActiveSubcarriers: int | None = None
    docsIf31CmtsDsOfdmChanSubcarrierSpacing: int | None = None
    docsIf31CmtsDsOfdmChanLowerGuardbandWidth: int | None = None
    docsIf31CmtsDsOfdmChanUpperGuardbandWidth: int | None = None
    docsIf31CmtsDsOfdmChanCyclicPrefix: int | None = None
    docsIf31CmtsDsOfdmChanRollOffPeriod: int | None = None
    docsIf31CmtsDsOfdmChanTimeInterleaverDepth: int | None = None
    docsIf31CmtsDsOfdmChanNumPilots: int | None = None
    docsIf31CmtsDsOfdmChanPilotScaleFactor: int | None = None
    docsIf31CmtsDsOfdmChanNcpModulation: int | None = None
    docsIf31CmtsDsOfdmChanUtilization: int | None = None
    docsIf31CmtsDsOfdmChanPowerAdjust: int | None = None


class DocsIf31CmtsDsOfdmChanRecord(BaseModel):
    index: int
    channel_id: int
    entry: DocsIf31CmtsDsOfdmChanEntry

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsIf31CmtsDsOfdmChanRecord | None:
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

        entry = DocsIf31CmtsDsOfdmChanEntry(
            docsIf31CmtsDsOfdmChanChannelId                =   await fetch("docsIf31CmtsDsOfdmChanChannelId", int),
            docsIf31CmtsDsOfdmChanLowerBdryFreq            =   await fetch("docsIf31CmtsDsOfdmChanLowerBdryFreq", int),
            docsIf31CmtsDsOfdmChanUpperBdryFreq            =   await fetch("docsIf31CmtsDsOfdmChanUpperBdryFreq", int),
            docsIf31CmtsDsOfdmChanLowerBdryEncompSpectrum  =   await fetch("docsIf31CmtsDsOfdmChanLowerBdryEncompSpectrum", int),
            docsIf31CmtsDsOfdmChanUpperBdryEncompSpectrum  =   await fetch("docsIf31CmtsDsOfdmChanUpperBdryEncompSpectrum", int),
            docsIf31CmtsDsOfdmChanPlcFreq                  =   await fetch("docsIf31CmtsDsOfdmChanPlcFreq", int),
            docsIf31CmtsDsOfdmChanSubcarrierZeroFreq       =   await fetch("docsIf31CmtsDsOfdmChanSubcarrierZeroFreq", int),
            docsIf31CmtsDsOfdmChanFirstActiveSubcarrierNum =   await fetch("docsIf31CmtsDsOfdmChanFirstActiveSubcarrierNum", int),
            docsIf31CmtsDsOfdmChanLastActiveSubcarrierNum  =   await fetch("docsIf31CmtsDsOfdmChanLastActiveSubcarrierNum", int),
            docsIf31CmtsDsOfdmChanNumActiveSubcarriers     =   await fetch("docsIf31CmtsDsOfdmChanNumActiveSubcarriers", int),
            docsIf31CmtsDsOfdmChanSubcarrierSpacing        =   await fetch("docsIf31CmtsDsOfdmChanSubcarrierSpacing", int),
            docsIf31CmtsDsOfdmChanLowerGuardbandWidth      =   await fetch("docsIf31CmtsDsOfdmChanLowerGuardbandWidth", int),
            docsIf31CmtsDsOfdmChanUpperGuardbandWidth      =   await fetch("docsIf31CmtsDsOfdmChanUpperGuardbandWidth", int),
            docsIf31CmtsDsOfdmChanCyclicPrefix             =   await fetch("docsIf31CmtsDsOfdmChanCyclicPrefix", int),
            docsIf31CmtsDsOfdmChanRollOffPeriod            =   await fetch("docsIf31CmtsDsOfdmChanRollOffPeriod", int),
            docsIf31CmtsDsOfdmChanTimeInterleaverDepth     =   await fetch("docsIf31CmtsDsOfdmChanTimeInterleaverDepth", int),
            docsIf31CmtsDsOfdmChanNumPilots                =   await fetch("docsIf31CmtsDsOfdmChanNumPilots", int),
            docsIf31CmtsDsOfdmChanPilotScaleFactor         =   await fetch("docsIf31CmtsDsOfdmChanPilotScaleFactor", int),
            docsIf31CmtsDsOfdmChanNcpModulation            =   await fetch("docsIf31CmtsDsOfdmChanNcpModulation", int),
            docsIf31CmtsDsOfdmChanUtilization              =   await fetch("docsIf31CmtsDsOfdmChanUtilization", int),
            docsIf31CmtsDsOfdmChanPowerAdjust              =   await fetch("docsIf31CmtsDsOfdmChanPowerAdjust", int),
        )

        return cls(
            index=index,
            channel_id=int(entry.docsIf31CmtsDsOfdmChanChannelId or 0),
            entry=entry,
        )

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: list[int]) -> list[DocsIf31CmtsDsOfdmChanRecord]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsIf31CmtsDsOfdmChanRecord] = []

        if not indices:
            logger.warning("No downstream OFDM channel indices found.")
            return results

        for index in indices:
            result = await cls.from_snmp(index, snmp)
            if result is not None:
                results.append(result)

        return results

    @classmethod
    async def get_all(cls, snmp: Snmp_v2c) -> list[DocsIf31CmtsDsOfdmChanRecord]:
        logger = logging.getLogger(cls.__name__)
        try:
            results = await snmp.walk("docsIf31CmtsDsOfdmChanChannelId")
        except Exception as exc:
            logger.warning(f"SNMP walk failed for docsIf31CmtsDsOfdmChanChannelId: {exc}")
            return []

        if not results:
            logger.warning("No downstream OFDM channel indices found.")
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
    "DocsIf31CmtsDsOfdmChanEntry",
    "DocsIf31CmtsDsOfdmChanRecord",
]

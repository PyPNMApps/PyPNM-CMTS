# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

from pydantic import BaseModel
from pypnm.snmp.snmp_v2c import Snmp_v2c


class DocsIf31CmtsUsOfdmaChanEntry(BaseModel):
    docsIf31CmtsUsOfdmaChanTemplateIndex: int | None = None
    docsIf31CmtsUsOfdmaChanConfigChangeCt: int | None = None
    docsIf31CmtsUsOfdmaChanTargetRxPower: int | None = None
    docsIf31CmtsUsOfdmaChanLowerBdryFreq: int | None = None
    docsIf31CmtsUsOfdmaChanUpperBdryFreq: int | None = None
    docsIf31CmtsUsOfdmaChanSubcarrierSpacing: int | None = None
    docsIf31CmtsUsOfdmaChanCyclicPrefix: int | None = None
    docsIf31CmtsUsOfdmaChanNumSymbolsPerFrame: int | None = None
    docsIf31CmtsUsOfdmaChanRollOffPeriod: int | None = None
    docsIf31CmtsUsOfdmaChanPreEqEnable: bool | None = None
    docsIf31CmtsUsOfdmaChanFineRngGuardband: int | None = None
    docsIf31CmtsUsOfdmaChanFineRngNumSubcarriers: int | None = None
    docsIf31CmtsUsOfdmaChanFineRngPreambleLen: int | None = None
    docsIf31CmtsUsOfdmaChanInitRngGuardband: int | None = None
    docsIf31CmtsUsOfdmaChanInitRngNumSubcarriers: int | None = None
    docsIf31CmtsUsOfdmaChanInitRngPreambleLen: int | None = None
    docsIf31CmtsUsOfdmaChanProvAttribMask: int | None = None
    docsIf31CmtsUsOfdmaChanTxBackoffStart: int | None = None
    docsIf31CmtsUsOfdmaChanTxBackoffEnd: int | None = None
    docsIf31CmtsUsOfdmaChanRangingBackoffStart: int | None = None
    docsIf31CmtsUsOfdmaChanRangingBackoffEnd: int | None = None
    docsIf31CmtsUsOfdmaChanUtilization: int | None = None
    docsIf31CmtsUsOfdmaChanId: int | None = None
    docsIf31CmtsUsOfdmaChanSubcarrierZeroFreq: int | None = None
    docsIf31CmtsUsOfdmaChanTargetMapInterval: int | None = None
    docsIf31CmtsUsOfdmaChanUpChannelTotalCms: int | None = None


class DocsIf31CmtsUsOfdmaChanRecord(BaseModel):
    index: int
    channel_id: int
    entry: DocsIf31CmtsUsOfdmaChanEntry

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsIf31CmtsUsOfdmaChanRecord | None:
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

        entry = DocsIf31CmtsUsOfdmaChanEntry(
            docsIf31CmtsUsOfdmaChanTemplateIndex            =   await fetch("docsIf31CmtsUsOfdmaChanTemplateIndex", int),
            docsIf31CmtsUsOfdmaChanConfigChangeCt           =   await fetch("docsIf31CmtsUsOfdmaChanConfigChangeCt", int),
            docsIf31CmtsUsOfdmaChanTargetRxPower            =   await fetch("docsIf31CmtsUsOfdmaChanTargetRxPower", int),
            docsIf31CmtsUsOfdmaChanLowerBdryFreq            =   await fetch("docsIf31CmtsUsOfdmaChanLowerBdryFreq", int),
            docsIf31CmtsUsOfdmaChanUpperBdryFreq            =   await fetch("docsIf31CmtsUsOfdmaChanUpperBdryFreq", int),
            docsIf31CmtsUsOfdmaChanSubcarrierSpacing        =   await fetch("docsIf31CmtsUsOfdmaChanSubcarrierSpacing", int),
            docsIf31CmtsUsOfdmaChanCyclicPrefix             =   await fetch("docsIf31CmtsUsOfdmaChanCyclicPrefix", int),
            docsIf31CmtsUsOfdmaChanNumSymbolsPerFrame       =   await fetch("docsIf31CmtsUsOfdmaChanNumSymbolsPerFrame", int),
            docsIf31CmtsUsOfdmaChanRollOffPeriod            =   await fetch("docsIf31CmtsUsOfdmaChanRollOffPeriod", int),
            docsIf31CmtsUsOfdmaChanPreEqEnable              =   await fetch("docsIf31CmtsUsOfdmaChanPreEqEnable", Snmp_v2c.truth_value),
            docsIf31CmtsUsOfdmaChanFineRngGuardband         =   await fetch("docsIf31CmtsUsOfdmaChanFineRngGuardband", int),
            docsIf31CmtsUsOfdmaChanFineRngNumSubcarriers    =   await fetch("docsIf31CmtsUsOfdmaChanFineRngNumSubcarriers", int),
            docsIf31CmtsUsOfdmaChanFineRngPreambleLen       =   await fetch("docsIf31CmtsUsOfdmaChanFineRngPreambleLen", int),
            docsIf31CmtsUsOfdmaChanInitRngGuardband         =   await fetch("docsIf31CmtsUsOfdmaChanInitRngGuardband", int),
            docsIf31CmtsUsOfdmaChanInitRngNumSubcarriers    =   await fetch("docsIf31CmtsUsOfdmaChanInitRngNumSubcarriers", int),
            docsIf31CmtsUsOfdmaChanInitRngPreambleLen       =   await fetch("docsIf31CmtsUsOfdmaChanInitRngPreambleLen", int),
            docsIf31CmtsUsOfdmaChanProvAttribMask           =   await fetch("docsIf31CmtsUsOfdmaChanProvAttribMask", int),
            docsIf31CmtsUsOfdmaChanTxBackoffStart           =   await fetch("docsIf31CmtsUsOfdmaChanTxBackoffStart", int),
            docsIf31CmtsUsOfdmaChanTxBackoffEnd             =   await fetch("docsIf31CmtsUsOfdmaChanTxBackoffEnd", int),
            docsIf31CmtsUsOfdmaChanRangingBackoffStart      =   await fetch("docsIf31CmtsUsOfdmaChanRangingBackoffStart", int),
            docsIf31CmtsUsOfdmaChanRangingBackoffEnd        =   await fetch("docsIf31CmtsUsOfdmaChanRangingBackoffEnd", int),
            docsIf31CmtsUsOfdmaChanUtilization              =   await fetch("docsIf31CmtsUsOfdmaChanUtilization", int),
            docsIf31CmtsUsOfdmaChanId                       =   await fetch("docsIf31CmtsUsOfdmaChanId", int),
            docsIf31CmtsUsOfdmaChanSubcarrierZeroFreq       =   await fetch("docsIf31CmtsUsOfdmaChanSubcarrierZeroFreq", int),
            docsIf31CmtsUsOfdmaChanTargetMapInterval        =   await fetch("docsIf31CmtsUsOfdmaChanTargetMapInterval", int),
            docsIf31CmtsUsOfdmaChanUpChannelTotalCms        =   await fetch("docsIf31CmtsUsOfdmaChanUpChannelTotalCms", int),
        )

        return cls(
            index=index,
            channel_id=int(entry.docsIf31CmtsUsOfdmaChanId or 0),
            entry=entry,
        )

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: list[int]) -> list[DocsIf31CmtsUsOfdmaChanRecord]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsIf31CmtsUsOfdmaChanRecord] = []

        if not indices:
            logger.warning("No upstream OFDMA channel indices found.")
            return results

        for index in indices:
            result = await cls.from_snmp(index, snmp)
            if result is not None:
                results.append(result)

        return results

    @classmethod
    async def get_all(cls, snmp: Snmp_v2c) -> list[DocsIf31CmtsUsOfdmaChanRecord]:
        logger = logging.getLogger(cls.__name__)
        try:
            results = await snmp.walk("docsIf31CmtsUsOfdmaChanId")
        except Exception as exc:
            logger.warning(f"SNMP walk failed for docsIf31CmtsUsOfdmaChanId: {exc}")
            return []

        if not results:
            logger.warning("No upstream OFDMA channel indices found.")
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
    "DocsIf31CmtsUsOfdmaChanEntry",
    "DocsIf31CmtsUsOfdmaChanRecord",
]

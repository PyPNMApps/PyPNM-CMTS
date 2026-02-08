# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

from pydantic import BaseModel
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import FileNameStr, MacAddressStr
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.lib.types import IntList


class DocsPnmCmtsUsOfdmaRxMerEntry(BaseModel):
    """docsPnmCmtsUsOfdmaRxMerEntry table fields."""

    docsPnmCmtsUsOfdmaRxMerEnable: bool | None = None
    docsPnmCmtsUsOfdmaRxMerCmMac: MacAddressStr | None = None
    docsPnmCmtsUsOfdmaRxMerPreEq: bool | None = None
    docsPnmCmtsUsOfdmaRxMerNumAvgs: int | None = None
    docsPnmCmtsUsOfdmaRxMerMeasStatus: int | None = None
    docsPnmCmtsUsOfdmaRxMerFileName: FileNameStr | None = None
    docsPnmCmtsUsOfdmaRxMerDestinationIndex: int | None = None


class DocsPnmCmtsUsOfdmaRxMerRecord(BaseModel):
    """Container for a single docsPnmCmtsUsOfdmaRxMer table row."""

    index: int
    entry: DocsPnmCmtsUsOfdmaRxMerEntry

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsPnmCmtsUsOfdmaRxMerRecord | None:
        logger = logging.getLogger(cls.__name__)

        def safe_cast(value: str, cast: Callable) -> int | float | str | bool | None:
            try:
                return cast(value)
            except Exception:
                return None

        def cast_mac(value: str) -> MacAddressStr | None:
            try:
                return MacAddressStr(str(MacAddress(value)))
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

        entry = DocsPnmCmtsUsOfdmaRxMerEntry(
            docsPnmCmtsUsOfdmaRxMerEnable=await fetch("docsPnmCmtsUsOfdmaRxMerEnable", Snmp_v2c.truth_value),
            docsPnmCmtsUsOfdmaRxMerCmMac=await fetch("docsPnmCmtsUsOfdmaRxMerCmMac", cast_mac),
            docsPnmCmtsUsOfdmaRxMerPreEq=await fetch("docsPnmCmtsUsOfdmaRxMerPreEq", Snmp_v2c.truth_value),
            docsPnmCmtsUsOfdmaRxMerNumAvgs=await fetch("docsPnmCmtsUsOfdmaRxMerNumAvgs", int),
            docsPnmCmtsUsOfdmaRxMerMeasStatus=await fetch("docsPnmCmtsUsOfdmaRxMerMeasStatus", int),
            docsPnmCmtsUsOfdmaRxMerFileName=await fetch("docsPnmCmtsUsOfdmaRxMerFileName", FileNameStr),
            docsPnmCmtsUsOfdmaRxMerDestinationIndex=await fetch("docsPnmCmtsUsOfdmaRxMerDestinationIndex", int),
        )

        return cls(index=index, entry=entry)

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: IntList) -> list[DocsPnmCmtsUsOfdmaRxMerRecord]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsPnmCmtsUsOfdmaRxMerRecord] = []
        if not indices:
            logger.warning("No docsPnmCmtsUsOfdmaRxMer indices found.")
            return results
        for index in indices:
            result = await cls.from_snmp(index, snmp)
            if result is not None:
                results.append(result)
        return results

    @classmethod
    async def get_all(cls, snmp: Snmp_v2c) -> list[DocsPnmCmtsUsOfdmaRxMerRecord]:
        logger = logging.getLogger(cls.__name__)
        try:
            results = await snmp.walk("docsPnmCmtsUsOfdmaRxMerMeasStatus")
        except Exception as exc:
            logger.warning(f"SNMP walk failed for docsPnmCmtsUsOfdmaRxMerMeasStatus: {exc}")
            return []

        if not results:
            logger.warning("No docsPnmCmtsUsOfdmaRxMer indices found.")
            return []

        indices_raw = Snmp_v2c.extract_last_oid_index(results)
        indices: IntList = []
        for value in indices_raw:
            if not isinstance(value, (int, str)):
                continue
            try:
                indices.append(int(value))
            except (TypeError, ValueError):
                continue

        return await cls.get(snmp, indices)


__all__ = [
    "DocsPnmCmtsUsOfdmaRxMerEntry",
    "DocsPnmCmtsUsOfdmaRxMerRecord",
]

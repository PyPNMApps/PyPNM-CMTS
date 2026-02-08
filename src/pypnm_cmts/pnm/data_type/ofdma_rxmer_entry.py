# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from pydantic import BaseModel
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import FileNameStr, InterfaceIndex, MacAddressStr
from pypnm.snmp.snmp_v2c import Snmp_v2c
from pysnmp.proto.rfc1902 import Integer32, OctetString

from pypnm_cmts.lib.types import (
    IntList,
    PnmDestinationIndex,
    PnmUsOfdmaRxMerMeasStatus,
    PnmUsOfdmaRxMerNumAvgs,
)
from pypnm_cmts.pnm.data_type.snmp_table_io import SnmpSetFieldSpec, SnmpTableIo


class DocsPnmCmtsUsOfdmaRxMerEntry(BaseModel):
    """docsPnmCmtsUsOfdmaRxMerEntry table fields."""

    docsPnmCmtsUsOfdmaRxMerEnable: bool | None = None
    docsPnmCmtsUsOfdmaRxMerCmMac: MacAddressStr | None = None
    docsPnmCmtsUsOfdmaRxMerPreEq: bool | None = None
    docsPnmCmtsUsOfdmaRxMerNumAvgs: PnmUsOfdmaRxMerNumAvgs | None = None
    docsPnmCmtsUsOfdmaRxMerMeasStatus: PnmUsOfdmaRxMerMeasStatus | None = None
    docsPnmCmtsUsOfdmaRxMerFileName: FileNameStr | None = None
    docsPnmCmtsUsOfdmaRxMerDestinationIndex: PnmDestinationIndex | None = None


class DocsPnmCmtsUsOfdmaRxMerRecord(BaseModel):
    """Container for a single docsPnmCmtsUsOfdmaRxMer table row."""

    index: InterfaceIndex
    entry: DocsPnmCmtsUsOfdmaRxMerEntry

    @classmethod
    async def set(
        cls,
        snmp: Snmp_v2c,
        index: int,
        entry: DocsPnmCmtsUsOfdmaRxMerEntry,
    ) -> bool:
        """
        Persist non-null writable docsPnmCmtsUsOfdmaRxMer fields for a single row index.

        Returns:
            bool: True when all requested sets succeed, else False.
        """
        logger = logging.getLogger(cls.__name__)

        updates_raw = entry.model_dump(exclude_none=True)
        if not updates_raw:
            logger.warning("No docsPnmCmtsUsOfdmaRxMer fields provided for set.")
            return True

        updates = [
            (field, value)
            for field, value in updates_raw.items()
            if field != "docsPnmCmtsUsOfdmaRxMerMeasStatus"
        ]
        if not updates:
            logger.warning("No writable docsPnmCmtsUsOfdmaRxMer fields provided for set.")
            return True

        field_specs = [
            SnmpSetFieldSpec(
                "docsPnmCmtsUsOfdmaRxMerEnable",
                Integer32,
                encoder=lambda value: SnmpTableIo.encode_truth_value(bool(value)),
            ),
            SnmpSetFieldSpec("docsPnmCmtsUsOfdmaRxMerCmMac", OctetString),
            SnmpSetFieldSpec(
                "docsPnmCmtsUsOfdmaRxMerPreEq",
                Integer32,
                encoder=lambda value: SnmpTableIo.encode_truth_value(bool(value)),
            ),
            SnmpSetFieldSpec("docsPnmCmtsUsOfdmaRxMerNumAvgs", Integer32),
            SnmpSetFieldSpec("docsPnmCmtsUsOfdmaRxMerFileName", OctetString),
            SnmpSetFieldSpec("docsPnmCmtsUsOfdmaRxMerDestinationIndex", Integer32),
        ]

        return await SnmpTableIo.set_fields(
            snmp=snmp,
            index=index,
            updates=updates,
            field_specs=field_specs,
            logger=logger,
        )

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsPnmCmtsUsOfdmaRxMerRecord | None:
        logger = logging.getLogger(cls.__name__)

        def cast_mac(value: str) -> MacAddressStr | None:
            try:
                return MacAddressStr(str(MacAddress(value)))
            except (TypeError, ValueError):
                return None

        entry = DocsPnmCmtsUsOfdmaRxMerEntry(
            docsPnmCmtsUsOfdmaRxMerEnable=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerEnable",
                logger=logger,
                cast=Snmp_v2c.truth_value,
            ),
            docsPnmCmtsUsOfdmaRxMerCmMac=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerCmMac",
                logger=logger,
                cast=cast_mac,
            ),
            docsPnmCmtsUsOfdmaRxMerPreEq=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerPreEq",
                logger=logger,
                cast=Snmp_v2c.truth_value,
            ),
            docsPnmCmtsUsOfdmaRxMerNumAvgs=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerNumAvgs",
                logger=logger,
                cast=PnmUsOfdmaRxMerNumAvgs,
            ),
            docsPnmCmtsUsOfdmaRxMerMeasStatus=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerMeasStatus",
                logger=logger,
                cast=PnmUsOfdmaRxMerMeasStatus,
            ),
            docsPnmCmtsUsOfdmaRxMerFileName=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerFileName",
                logger=logger,
                cast=FileNameStr,
            ),
            docsPnmCmtsUsOfdmaRxMerDestinationIndex=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmCmtsUsOfdmaRxMerDestinationIndex",
                logger=logger,
                cast=PnmDestinationIndex,
            ),
        )

        return cls(index=InterfaceIndex(index), entry=entry)

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

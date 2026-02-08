# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from pydantic import BaseModel
from pypnm.snmp.modules import InetAddressType
from pypnm.snmp.snmp_v2c import Snmp_v2c
from pysnmp.proto.rfc1902 import Integer32, OctetString

from pypnm_cmts.lib.constants import DocsPnmBulkDataTransferProtocol
from pypnm_cmts.lib.types import (
    HostNameStr,
    InetAddressStr,
    IntList,
    PnmBaseUriStr,
    PnmDestinationIndex,
    PnmDestinationPort,
    PnmRowStatus,
)
from pypnm_cmts.pnm.data_type.snmp_table_io import SnmpSetFieldSpec, SnmpTableIo


class DocsPnmBulkDataTransferCfgEntry(BaseModel):
    """docsPnmBulkDataTransferCfgEntry table fields."""

    docsPnmBulkDataTransferCfgDestIndex: PnmDestinationIndex | None = None
    docsPnmBulkDataTransferCfgDestHostname: HostNameStr | None = None
    docsPnmBulkDataTransferCfgDestHostIpAddrType: InetAddressType | None = None
    docsPnmBulkDataTransferCfgDestHostIpAddress: InetAddressStr | None = None
    docsPnmBulkDataTransferCfgDestPort: PnmDestinationPort | None = None
    docsPnmBulkDataTransferCfgDestBaseUri: PnmBaseUriStr | None = None
    docsPnmBulkDataTransferCfgProtocol: DocsPnmBulkDataTransferProtocol | None = None
    docsPnmBulkDataTransferCfgLocalStore: bool | None = None
    docsPnmBulkDataTransferCfgRowStatus: PnmRowStatus | None = None


class DocsPnmBulkDataTransferCfgRecord(BaseModel):
    """Container for a single docsPnmBulkDataTransferCfg table row."""

    index: int
    entry: DocsPnmBulkDataTransferCfgEntry

    @classmethod
    async def set(
        cls,
        snmp: Snmp_v2c,
        index: int,
        entry: DocsPnmBulkDataTransferCfgEntry,
    ) -> bool:
        """
        Persist non-null docsPnmBulkDataTransferCfg fields for a single row index.

        Returns:
            bool: True when all requested sets succeed, else False.
        """
        logger = logging.getLogger(cls.__name__)

        updates_raw = entry.model_dump(exclude_none=True)
        if not updates_raw:
            logger.warning("No docsPnmBulkDataTransferCfg fields provided for set.")
            return True

        updates = [
            (field, value)
            for field, value in updates_raw.items()
            if field != "docsPnmBulkDataTransferCfgDestIndex"
        ]
        if not updates:
            logger.warning("No writable docsPnmBulkDataTransferCfg fields provided for set.")
            return True

        field_specs = [
            SnmpSetFieldSpec("docsPnmBulkDataTransferCfgDestHostname", OctetString),
            SnmpSetFieldSpec(
                "docsPnmBulkDataTransferCfgDestHostIpAddrType",
                Integer32,
                encoder=lambda value: int(value),
            ),
            SnmpSetFieldSpec("docsPnmBulkDataTransferCfgDestHostIpAddress", OctetString),
            SnmpSetFieldSpec("docsPnmBulkDataTransferCfgDestPort", Integer32),
            SnmpSetFieldSpec("docsPnmBulkDataTransferCfgDestBaseUri", OctetString),
            SnmpSetFieldSpec(
                "docsPnmBulkDataTransferCfgProtocol",
                Integer32,
                encoder=lambda value: int(value),
            ),
            SnmpSetFieldSpec(
                "docsPnmBulkDataTransferCfgLocalStore",
                Integer32,
                encoder=lambda value: SnmpTableIo.encode_truth_value(bool(value)),
            ),
            SnmpSetFieldSpec("docsPnmBulkDataTransferCfgRowStatus", Integer32),
        ]
        return await SnmpTableIo.set_fields(
            snmp=snmp,
            index=index,
            updates=updates,
            field_specs=field_specs,
            logger=logger,
        )

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsPnmBulkDataTransferCfgRecord | None:
        logger = logging.getLogger(cls.__name__)

        entry = DocsPnmBulkDataTransferCfgEntry(
            docsPnmBulkDataTransferCfgDestIndex=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgDestIndex",
                logger=logger,
                cast=PnmDestinationIndex,
            ),
            docsPnmBulkDataTransferCfgDestHostname=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgDestHostname",
                logger=logger,
                cast=HostNameStr,
            ),
            docsPnmBulkDataTransferCfgDestHostIpAddrType=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgDestHostIpAddrType",
                logger=logger,
                cast=lambda value: InetAddressType(int(value)),
            ),
            docsPnmBulkDataTransferCfgDestHostIpAddress=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgDestHostIpAddress",
                logger=logger,
                cast=InetAddressStr,
            ),
            docsPnmBulkDataTransferCfgDestPort=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgDestPort",
                logger=logger,
                cast=PnmDestinationPort,
            ),
            docsPnmBulkDataTransferCfgDestBaseUri=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgDestBaseUri",
                logger=logger,
                cast=PnmBaseUriStr,
            ),
            docsPnmBulkDataTransferCfgProtocol=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgProtocol",
                logger=logger,
                cast=lambda value: DocsPnmBulkDataTransferProtocol(int(value)),
            ),
            docsPnmBulkDataTransferCfgLocalStore=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgLocalStore",
                logger=logger,
                cast=Snmp_v2c.truth_value,
            ),
            docsPnmBulkDataTransferCfgRowStatus=await SnmpTableIo.fetch_field(
                snmp=snmp,
                index=index,
                field="docsPnmBulkDataTransferCfgRowStatus",
                logger=logger,
                cast=PnmRowStatus,
            ),
        )

        return cls(index=index, entry=entry)

    @classmethod
    async def get(cls, snmp: Snmp_v2c, indices: IntList) -> list[DocsPnmBulkDataTransferCfgRecord]:
        logger = logging.getLogger(cls.__name__)
        results: list[DocsPnmBulkDataTransferCfgRecord] = []
        if not indices:
            logger.warning("No docsPnmBulkDataTransferCfg indices found.")
            return results
        for index in indices:
            result = await cls.from_snmp(index, snmp)
            if result is not None:
                results.append(result)
        return results

    @classmethod
    async def get_all(cls, snmp: Snmp_v2c) -> list[DocsPnmBulkDataTransferCfgRecord]:
        logger = logging.getLogger(cls.__name__)
        try:
            results = await snmp.walk("docsPnmBulkDataTransferCfgRowStatus")
        except Exception as exc:
            logger.warning(f"SNMP walk failed for docsPnmBulkDataTransferCfgRowStatus: {exc}")
            return []

        if not results:
            logger.warning("No docsPnmBulkDataTransferCfg indices found.")
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
    "DocsPnmBulkDataTransferCfgEntry",
    "DocsPnmBulkDataTransferCfgRecord",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable

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

    @staticmethod
    def _encode_truth_value(value: bool) -> int:
        """Encode SNMP TruthValue as true(1) / false(2)."""
        return 1 if value else 2

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

        updates = entry.model_dump(exclude_none=True)
        if not updates:
            logger.warning("No docsPnmBulkDataTransferCfg fields provided for set.")
            return True

        updates.pop("docsPnmBulkDataTransferCfgDestIndex", None)
        if not updates:
            logger.warning("No writable docsPnmBulkDataTransferCfg fields provided for set.")
            return True

        field_encoders: dict[str, Callable[[object], object]] = {
            "docsPnmBulkDataTransferCfgDestHostIpAddrType": lambda value: int(value),
            "docsPnmBulkDataTransferCfgProtocol": lambda value: int(value),
            "docsPnmBulkDataTransferCfgLocalStore": lambda value: cls._encode_truth_value(bool(value)),
        }
        field_types: dict[str, Snmp_v2c.SnmpValueType] = {
            "docsPnmBulkDataTransferCfgDestHostname": OctetString,
            "docsPnmBulkDataTransferCfgDestHostIpAddrType": Integer32,
            "docsPnmBulkDataTransferCfgDestHostIpAddress": OctetString,
            "docsPnmBulkDataTransferCfgDestPort": Integer32,
            "docsPnmBulkDataTransferCfgDestBaseUri": OctetString,
            "docsPnmBulkDataTransferCfgProtocol": Integer32,
            "docsPnmBulkDataTransferCfgLocalStore": Integer32,
            "docsPnmBulkDataTransferCfgRowStatus": Integer32,
        }

        for field, raw_value in updates.items():
            value = raw_value
            try:
                encoder = field_encoders.get(field)
                if encoder is not None:
                    value = encoder(raw_value)
                value_type = field_types[field]
                result = await snmp.set(f"{field}.{index}", value, value_type)
                if not result:
                    logger.warning("SNMP set returned no result for %s.%s", field, index)
                    return False
            except Exception as exc:
                logger.warning("SNMP set failed for %s.%s: %s", field, index, exc)
                return False

        return True

    @classmethod
    async def from_snmp(cls, index: int, snmp: Snmp_v2c) -> DocsPnmBulkDataTransferCfgRecord | None:
        logger = logging.getLogger(cls.__name__)

        def safe_cast(value: str, cast: Callable) -> object | None:
            try:
                return cast(value)
            except Exception:
                return None

        async def fetch(field: str, cast: Callable | None = None) -> object | None:
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

        entry = DocsPnmBulkDataTransferCfgEntry(
            docsPnmBulkDataTransferCfgDestIndex=await fetch("docsPnmBulkDataTransferCfgDestIndex", PnmDestinationIndex),
            docsPnmBulkDataTransferCfgDestHostname=await fetch("docsPnmBulkDataTransferCfgDestHostname", HostNameStr),
            docsPnmBulkDataTransferCfgDestHostIpAddrType=await fetch(
                "docsPnmBulkDataTransferCfgDestHostIpAddrType",
                lambda value: InetAddressType(int(value)),
            ),
            docsPnmBulkDataTransferCfgDestHostIpAddress=await fetch("docsPnmBulkDataTransferCfgDestHostIpAddress", InetAddressStr),
            docsPnmBulkDataTransferCfgDestPort=await fetch("docsPnmBulkDataTransferCfgDestPort", PnmDestinationPort),
            docsPnmBulkDataTransferCfgDestBaseUri=await fetch("docsPnmBulkDataTransferCfgDestBaseUri", PnmBaseUriStr),
            docsPnmBulkDataTransferCfgProtocol=await fetch(
                "docsPnmBulkDataTransferCfgProtocol",
                lambda value: DocsPnmBulkDataTransferProtocol(int(value)),
            ),
            docsPnmBulkDataTransferCfgLocalStore=await fetch("docsPnmBulkDataTransferCfgLocalStore", Snmp_v2c.truth_value),
            docsPnmBulkDataTransferCfgRowStatus=await fetch("docsPnmBulkDataTransferCfgRowStatus", PnmRowStatus),
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

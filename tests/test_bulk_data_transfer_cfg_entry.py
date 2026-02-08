# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio

import pytest
from pypnm.snmp.snmp_v2c import Snmp_v2c
from pysnmp.proto.rfc1902 import Integer32, OctetString

from pypnm_cmts.lib.constants import DocsPnmBulkDataTransferProtocol
from pypnm_cmts.pnm.data_type.bulk_data_transfer_cfg_entry import (
    DocsPnmBulkDataTransferCfgEntry,
    DocsPnmBulkDataTransferCfgRecord,
)


class _DummySnmp:
    def __init__(self, mapping: dict[str, str], walk_results: list[str] | None = None) -> None:
        self._mapping = mapping
        self._walk_results = walk_results or []

    async def get(self, oid: str) -> str | None:
        return self._mapping.get(oid)

    async def walk(self, oid: str) -> list[str]:
        return self._walk_results


class _DummySnmpSet:
    def __init__(self, should_fail_oid: str | None = None) -> None:
        self.calls: list[tuple[str, object, object]] = []
        self._should_fail_oid = should_fail_oid

    async def set(self, oid: str, value: object, value_type: object) -> list[object] | None:
        self.calls.append((oid, value, value_type))
        if self._should_fail_oid is not None and oid == self._should_fail_oid:
            return None
        return [object()]


def test_docs_pnm_bulk_data_transfer_cfg_from_snmp(monkeypatch: pytest.MonkeyPatch) -> None:
    index = 7
    mapping = {
        f"docsPnmBulkDataTransferCfgDestIndex.{index}": "7",
        f"docsPnmBulkDataTransferCfgDestHostname.{index}": "pnm.example.net",
        f"docsPnmBulkDataTransferCfgDestHostIpAddrType.{index}": "1",
        f"docsPnmBulkDataTransferCfgDestHostIpAddress.{index}": "192.168.10.20",
        f"docsPnmBulkDataTransferCfgDestPort.{index}": "69",
        f"docsPnmBulkDataTransferCfgDestBaseUri.{index}": "/pnm/results",
        f"docsPnmBulkDataTransferCfgProtocol.{index}": "1",
        f"docsPnmBulkDataTransferCfgLocalStore.{index}": "1",
        f"docsPnmBulkDataTransferCfgRowStatus.{index}": "1",
    }
    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)
    snmp = _DummySnmp(mapping)

    record = asyncio.run(DocsPnmBulkDataTransferCfgRecord.from_snmp(index, snmp))
    assert record is not None
    assert record.index == 7
    assert record.entry.docsPnmBulkDataTransferCfgDestIndex == 7
    assert record.entry.docsPnmBulkDataTransferCfgDestHostname == "pnm.example.net"
    assert record.entry.docsPnmBulkDataTransferCfgDestHostIpAddrType == 1
    assert record.entry.docsPnmBulkDataTransferCfgDestHostIpAddress == "192.168.10.20"
    assert record.entry.docsPnmBulkDataTransferCfgDestPort == 69
    assert record.entry.docsPnmBulkDataTransferCfgDestBaseUri == "/pnm/results"
    assert record.entry.docsPnmBulkDataTransferCfgProtocol == 1
    assert record.entry.docsPnmBulkDataTransferCfgLocalStore is True
    assert record.entry.docsPnmBulkDataTransferCfgRowStatus == 1


def test_docs_pnm_bulk_data_transfer_cfg_get_all(monkeypatch: pytest.MonkeyPatch) -> None:
    walk_results = [
        "1.3.6.1.4.1.4491.2.1.27.1.2.1.9.10",
        "1.3.6.1.4.1.4491.2.1.27.1.2.1.9.11",
    ]
    mapping = {
        "docsPnmBulkDataTransferCfgDestIndex.10": "10",
        "docsPnmBulkDataTransferCfgDestIndex.11": "11",
    }
    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)
    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", lambda rows: [10, 11])
    snmp = _DummySnmp(mapping=mapping, walk_results=walk_results)

    records = asyncio.run(DocsPnmBulkDataTransferCfgRecord.get_all(snmp))
    assert len(records) == 2
    assert records[0].index == 10
    assert records[1].index == 11


def test_docs_pnm_bulk_data_transfer_cfg_set() -> None:
    snmp = _DummySnmpSet()
    entry = DocsPnmBulkDataTransferCfgEntry(
        docsPnmBulkDataTransferCfgDestIndex=7,
        docsPnmBulkDataTransferCfgDestHostname="pnm.example.net",
        docsPnmBulkDataTransferCfgDestHostIpAddrType=1,
        docsPnmBulkDataTransferCfgDestHostIpAddress="192.168.10.20",
        docsPnmBulkDataTransferCfgDestPort=69,
        docsPnmBulkDataTransferCfgDestBaseUri="/pnm/results",
        docsPnmBulkDataTransferCfgProtocol=DocsPnmBulkDataTransferProtocol.TFTP,
        docsPnmBulkDataTransferCfgLocalStore=True,
        docsPnmBulkDataTransferCfgRowStatus=1,
    )

    ok = asyncio.run(DocsPnmBulkDataTransferCfgRecord.set(snmp, index=7, entry=entry))
    assert ok is True
    assert len(snmp.calls) == 8
    assert ("docsPnmBulkDataTransferCfgDestHostname.7", "pnm.example.net", OctetString) in snmp.calls
    assert ("docsPnmBulkDataTransferCfgDestHostIpAddrType.7", 1, Integer32) in snmp.calls
    assert ("docsPnmBulkDataTransferCfgProtocol.7", 1, Integer32) in snmp.calls
    assert ("docsPnmBulkDataTransferCfgLocalStore.7", 1, Integer32) in snmp.calls


def test_docs_pnm_bulk_data_transfer_cfg_set_failure() -> None:
    snmp = _DummySnmpSet(should_fail_oid="docsPnmBulkDataTransferCfgDestPort.7")
    entry = DocsPnmBulkDataTransferCfgEntry(
        docsPnmBulkDataTransferCfgDestHostname="pnm.example.net",
        docsPnmBulkDataTransferCfgDestPort=69,
    )

    ok = asyncio.run(DocsPnmBulkDataTransferCfgRecord.set(snmp, index=7, entry=entry))
    assert ok is False

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio

import pytest
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.pnm.data_type.ofdma_rxmer_entry import (
    DocsPnmCmtsUsOfdmaRxMerRecord,
)


class _DummySnmp:
    def __init__(self, mapping: dict[str, str], walk_results: list[str] | None = None) -> None:
        self._mapping = mapping
        self._walk_results = walk_results or []

    async def get(self, oid: str) -> str | None:
        return self._mapping.get(oid)

    async def walk(self, oid: str) -> list[str]:
        return self._walk_results


def test_docs_pnm_cmts_us_ofdma_rxmer_from_snmp(monkeypatch: pytest.MonkeyPatch) -> None:
    index = 42
    mapping = {
        f"docsPnmCmtsUsOfdmaRxMerEnable.{index}": "1",
        f"docsPnmCmtsUsOfdmaRxMerCmMac.{index}": "0x001122334455",
        f"docsPnmCmtsUsOfdmaRxMerPreEq.{index}": "2",
        f"docsPnmCmtsUsOfdmaRxMerNumAvgs.{index}": "25",
        f"docsPnmCmtsUsOfdmaRxMerMeasStatus.{index}": "3",
        f"docsPnmCmtsUsOfdmaRxMerFileName.{index}": "PNMCcapRxMER_test",
        f"docsPnmCmtsUsOfdmaRxMerDestinationIndex.{index}": "7",
    }
    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)
    snmp = _DummySnmp(mapping)

    record = asyncio.run(DocsPnmCmtsUsOfdmaRxMerRecord.from_snmp(index, snmp))
    assert record is not None
    assert record.index == 42
    assert record.entry.docsPnmCmtsUsOfdmaRxMerEnable is True
    assert record.entry.docsPnmCmtsUsOfdmaRxMerCmMac == "00:11:22:33:44:55"
    assert record.entry.docsPnmCmtsUsOfdmaRxMerPreEq is False
    assert record.entry.docsPnmCmtsUsOfdmaRxMerNumAvgs == 25
    assert record.entry.docsPnmCmtsUsOfdmaRxMerMeasStatus == 3
    assert record.entry.docsPnmCmtsUsOfdmaRxMerFileName == "PNMCcapRxMER_test"
    assert record.entry.docsPnmCmtsUsOfdmaRxMerDestinationIndex == 7


def test_docs_pnm_cmts_us_ofdma_rxmer_get_all(monkeypatch: pytest.MonkeyPatch) -> None:
    walk_results = [
        "1.3.6.1.4.1.4491.2.1.27.1.3.7.1.5.10",
        "1.3.6.1.4.1.4491.2.1.27.1.3.7.1.5.11",
    ]
    mapping = {
        "docsPnmCmtsUsOfdmaRxMerEnable.10": "1",
        "docsPnmCmtsUsOfdmaRxMerEnable.11": "1",
    }
    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)
    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", lambda rows: [10, 11])
    snmp = _DummySnmp(mapping=mapping, walk_results=walk_results)

    records = asyncio.run(DocsPnmCmtsUsOfdmaRxMerRecord.get_all(snmp))
    assert len(records) == 2
    assert records[0].index == 10
    assert records[1].index == 11

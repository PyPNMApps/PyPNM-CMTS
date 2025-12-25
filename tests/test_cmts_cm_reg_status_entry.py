# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio

import pytest
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.data_type.cmts_cm_reg_status_entry import (
    DocsIf3CmtsCmRegStatusIdEntry,
)


class _DummySnmp:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    async def get(self, oid: str) -> str | None:
        return self._mapping.get(oid)


def test_docsif3_cmts_cm_reg_status_entry_from_snmp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = 42
    mapping = {
        f"docsIf3CmtsCmRegStatusMacAddr.{index}": "0x001122334455",
        f"docsIf3CmtsCmRegStatusIPv6Addr.{index}": "2001:db8::1",
        f"docsIf3CmtsCmRegStatusIPv6LinkLocal.{index}": "fe80::1",
        f"docsIf3CmtsCmRegStatusIPv4Addr.{index}": "192.168.0.10",
        f"docsIf3CmtsCmRegStatusValue.{index}": "3",
        f"docsIf3CmtsCmRegStatusMdIfIndex.{index}": "0",
        f"docsIf3CmtsCmRegStatusMdCmSgId.{index}": "7",
        f"docsIf3CmtsCmRegStatusRcpId.{index}": "0000000000",
        f"docsIf3CmtsCmRegStatusRccStatusId.{index}": "0x02",
        f"docsIf3CmtsCmRegStatusRcsId.{index}": "11",
        f"docsIf3CmtsCmRegStatusTcsId.{index}": "12",
        f"docsIf3CmtsCmRegStatusQosVersion.{index}": "1",
        f"docsIf3CmtsCmRegStatusLastRegTime.{index}": "2025-01-01T00:00:00",
        f"docsIf3CmtsCmRegStatusAddrResolutionReqs.{index}": "9",
        f"docsIf3CmtsCmRegStatusEnergyMgtEnabled.{index}": "0x01",
        f"docsIf3CmtsCmRegStatusEnergyMgtOperStatus.{index}": "0x00",
    }

    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)
    snmp = _DummySnmp(mapping)

    entry = asyncio.run(DocsIf3CmtsCmRegStatusIdEntry.from_snmp(index, snmp))

    assert entry.status_id == index
    assert entry.entry.docsIf3CmtsCmRegStatusMacAddr == "00:11:22:33:44:55"
    assert entry.entry.docsIf3CmtsCmRegStatusIPv4Addr == "192.168.0.10"
    assert entry.entry.docsIf3CmtsCmRegStatusIPv6Addr == "2001:db8::1"
    assert entry.entry.docsIf3CmtsCmRegStatusIPv6LinkLocal == "fe80::1"
    assert entry.entry.docsIf3CmtsCmRegStatusValue == 3
    assert entry.entry.docsIf3CmtsCmRegStatusMdIfIndex == 0
    assert entry.entry.docsIf3CmtsCmRegStatusMdCmSgId == 7
    assert entry.entry.docsIf3CmtsCmRegStatusRccStatusId == 2
    assert entry.entry.docsIf3CmtsCmRegStatusEnergyMgtEnabled == 1
    assert entry.entry.docsIf3CmtsCmRegStatusEnergyMgtOperStatus == 0

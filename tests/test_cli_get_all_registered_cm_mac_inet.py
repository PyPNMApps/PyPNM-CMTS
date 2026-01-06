# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio

import pytest

from pypnm_cmts.examples.cli.get_all_registered_cm_mac_inet import RegisterCmMacInetCli


class _DummySnmp:
    def __init__(self, get_map: dict[str, str], sg_result: object) -> None:
        self._get_map = get_map
        self._sg_result = sg_result

    async def walk(self, oid: str) -> object | None:
        if oid == "docsIf3CmtsCmRegStatusMdCmSgId":
            return self._sg_result
        return []

    async def get(self, oid: str) -> object | None:
        return self._get_map.get(oid, "")


class _DummySnmpFactory:
    def __init__(self, get_map: dict[str, str], sg_result: object) -> None:
        self._get_map = get_map
        self._sg_result = sg_result

    def __call__(self, *args: object, **kwargs: object) -> _DummySnmp:
        return _DummySnmp(self._get_map, self._sg_result)

    @staticmethod
    def extract_last_oid_index(_: object) -> list[int]:
        return [1001, 1002]

    @staticmethod
    def snmp_get_result_value(_: object) -> list[str]:
        return ["7", "9"]

    @staticmethod
    def get_result_value(raw: object) -> object:
        return raw


def test_fetch_all_by_group(monkeypatch: pytest.MonkeyPatch) -> None:
    sg_result = object()
    get_map = {
        "docsIf3CmtsCmRegStatusMacAddr.1001": "0x001122334455",
        "docsIf3CmtsCmRegStatusIPv4Addr.1001": "192.168.0.10",
        "docsIf3CmtsCmRegStatusIPv6Addr.1001": "2001:db8::1",
        "docsIf3CmtsCmRegStatusIPv6LinkLocal.1001": "fe80::1",
        "docsIf3CmtsCmRegStatusMacAddr.1002": "0x001122334456",
        "docsIf3CmtsCmRegStatusIPv4Addr.1002": "192.168.0.11",
        "docsIf3CmtsCmRegStatusIPv6Addr.1002": "2001:db8::2",
        "docsIf3CmtsCmRegStatusIPv6LinkLocal.1002": "fe80::2",
    }

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.get_all_registered_cm_mac_inet.Snmp_v2c",
        _DummySnmpFactory(get_map, sg_result),
    )
    monkeypatch.setattr(
        "pypnm.snmp.snmp_v2c.Snmp_v2c.extract_last_oid_index",
        lambda _: [1001, 1002],
    )
    monkeypatch.setattr(
        "pypnm.snmp.snmp_v2c.Snmp_v2c.snmp_get_result_value",
        lambda _: ["7", "9"],
    )
    monkeypatch.setattr(
        "pypnm.snmp.snmp_v2c.Snmp_v2c.get_result_value",
        lambda raw: raw,
    )

    from pypnm.lib.inet import Inet

    results = asyncio.run(
        RegisterCmMacInetCli.fetch_all_by_group(Inet("192.168.0.100"), "public")
    )

    assert set(results.keys()) == {7, 9}
    assert results[7][0][1] == "00:11:22:33:44:55"
    assert results[9][0][1] == "00:11:22:33:44:56"

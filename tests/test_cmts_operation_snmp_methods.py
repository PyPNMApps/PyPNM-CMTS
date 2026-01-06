# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from pypnm.lib.inet import Inet
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import InterfaceIndex
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.docsis.data_type.cmts_cm_reg_status_entry import (
    DocsIf3CmtsCmRegStatusEntry,
    DocsIf3CmtsCmRegStatusIdEntry,
)
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.types import (
    ChSetId,
    CmRegSgId,
    MdCmSgId,
    MdDsSgId,
    MdUsSgId,
    RegisterCmMacInetAddress,
)


class _DummySnmp:
    def __init__(self, mac_result: object, sg_result: object) -> None:
        self._mac_result = mac_result
        self._sg_result = sg_result

    async def walk(self, oid: str) -> object | None:
        if oid == "docsIf3CmtsCmRegStatusMacAddr":
            return self._mac_result
        if oid == "docsIf3CmtsCmRegStatusMdCmSgId":
            return self._sg_result
        if oid in ("docsIf3MdNodeStatusMdDsSgId", "docsIf3MdNodeStatusMdUsSgId"):
            return self._mac_result
        return None

    async def get(self, oid: str) -> object | None:
        return None


class _DummyOid:
    def __init__(self, values: list[int]) -> None:
        self._values = values

    def __iter__(self) -> Iterator[int]:
        return iter(self._values)

    def __str__(self) -> str:
        return ".".join(str(value) for value in self._values)


class _DummyValue:
    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value


class _DummySnmpMapping:
    def __init__(self, mapping: dict[str, list[tuple[object, object]]]) -> None:
        self._mapping = mapping

    async def walk(self, oid: str) -> object | None:
        return self._mapping.get(oid, [])


class _DummySnmpGetMapping:
    def __init__(
        self,
        get_map: dict[str, object],
        walk_map: dict[str, list[tuple[object, object]]] | None = None,
    ) -> None:
        self._get_map = get_map
        self._walk_map = walk_map or {}

    async def walk(self, oid: str) -> object | None:
        return self._walk_map.get(oid, [])

    async def get(self, oid: str) -> object | None:
        return self._get_map.get(oid)


def test_get_docsif3_md_node_status_ds_sg_id() -> None:
    base_oid = Snmp_v2c.resolve_oid("docsIf3MdNodeStatusMdDsSgId")
    base = [int(part) for part in base_oid.strip(".").split(".")]
    entries = [
        base + [1049, 6, 78, 79, 68, 69, 45, 49, 3147266],
        base + [1050, 6, 78, 79, 68, 69, 45, 50, 3213825],
    ]
    varbinds = [
        (_DummyOid(entries[0]), _DummyValue("6")),
        (_DummyOid(entries[1]), _DummyValue("10")),
    ]

    snmp = _DummySnmpMapping(
        {"docsIf3MdNodeStatusMdDsSgId": varbinds}
    )
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )
    results = asyncio.run(operation.getDocsIf3MdNodeStatusMdDsSgId())

    assert len(results) == 2
    assert str(results[0][1]) == "NODE-1"
    assert int(results[0][2]) == 6


def test_get_docsif3_md_node_status_us_sg_id() -> None:
    base_oid = Snmp_v2c.resolve_oid("docsIf3MdNodeStatusMdUsSgId")
    base = [int(part) for part in base_oid.strip(".").split(".")]
    entries = [base + [1049, 6, 78, 79, 68, 69, 45, 49, 3147266]]
    varbinds = [
        (_DummyOid(entries[0]), _DummyValue("2")),
    ]

    snmp = _DummySnmpMapping(
        {"docsIf3MdNodeStatusMdUsSgId": varbinds}
    )
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )
    results = asyncio.run(operation.getDocsIf3MdNodeStatusMdUsSgId())

    assert len(results) == 1
    assert str(results[0][1]) == "NODE-1"
    assert int(results[0][2]) == 2


def test_get_docsif3_md_ds_sg_status_ch_set_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.get_result_value",
        lambda value: str(value) if value is not None else None,
    )

    snmp = _DummySnmpGetMapping(
        {"docsIf3MdDsSgStatusChSetId.1049.6": _DummyValue("12")}
    )
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    exists, ch_set_id = asyncio.run(
        operation.getDocsIf3MdDsSgStatusChSetId(
            InterfaceIndex(1049),
            MdDsSgId(6),
        )
    )

    assert bool(exists) is True
    assert ch_set_id == ChSetId(12)


def test_get_docsif3_md_us_sg_status_ch_set_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.get_result_value",
        lambda value: str(value) if value is not None else None,
    )

    snmp = _DummySnmpGetMapping(
        {"docsIf3MdUsSgStatusChSetId.1049.2": _DummyValue("9")}
    )
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    exists, ch_set_id = asyncio.run(
        operation.getDocsIf3MdUsSgStatusChSetId(
            InterfaceIndex(1049),
            MdUsSgId(2),
        )
    )

    assert bool(exists) is True
    assert ch_set_id == ChSetId(9)


def test_get_docsif3_ds_ch_set_ch_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.get_result_value",
        lambda value: str(value) if value is not None else None,
    )

    snmp = _DummySnmpGetMapping(
        {"docsIf3DsChSetChList.1049.12": _DummyValue("1, 2, 3")}
    )
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    channels = asyncio.run(
        operation.getDocsIf3DsChSetChList(InterfaceIndex(1049), ChSetId(12))
    )

    assert channels == [1, 2, 3]


def test_get_docsif3_us_ch_set_ch_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.get_result_value",
        lambda value: str(value) if value is not None else None,
    )

    snmp = _DummySnmpGetMapping(
        {"docsIf3UsChSetChList.1049.9": _DummyValue("4 5 6")}
    )
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    channels = asyncio.run(
        operation.getDocsIf3UsChSetChList(InterfaceIndex(1049), ChSetId(9))
    )

    assert channels == [4, 5, 6]


def test_get_service_group_topology(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get_result_value(result: object) -> str | None:
        if isinstance(result, tuple):
            return str(result[1])
        if result is None:
            return None
        return str(result)

    monkeypatch.setattr(
        "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.get_result_value",
        _fake_get_result_value,
    )

    async def _groups() -> list[CmtsServiceGroupModel]:
        return [
            CmtsServiceGroupModel(
                if_index=InterfaceIndex(1049),
                node_name="NODE-1",
                md_cm_sg_id=MdCmSgId(3147266),
                md_ds_sg_id=MdDsSgId(6),
                md_us_sg_id=MdUsSgId(2),
            )
        ]

    ds_base = Snmp_v2c.resolve_oid("docsIf3MdDsSgStatusChSetId")
    us_base = Snmp_v2c.resolve_oid("docsIf3MdUsSgStatusChSetId")
    ds_list_base = Snmp_v2c.resolve_oid("docsIf3DsChSetChList")
    us_list_base = Snmp_v2c.resolve_oid("docsIf3UsChSetChList")

    ds_oid = [int(part) for part in ds_base.strip(".").split(".")] + [1049, 6]
    us_oid = [int(part) for part in us_base.strip(".").split(".")] + [1049, 2]
    ds_list_oid = [int(part) for part in ds_list_base.strip(".").split(".")] + [1049, 12]
    us_list_oid = [int(part) for part in us_list_base.strip(".").split(".")] + [1049, 9]

    walk_map = {
        "docsIf3MdDsSgStatusChSetId": [(_DummyOid(ds_oid), _DummyValue("12"))],
        "docsIf3MdUsSgStatusChSetId": [(_DummyOid(us_oid), _DummyValue("9"))],
        "docsIf3DsChSetChList": [(_DummyOid(ds_list_oid), _DummyValue("1,2"))],
        "docsIf3UsChSetChList": [(_DummyOid(us_list_oid), _DummyValue("3,4"))],
    }

    snmp = _DummySnmpGetMapping({}, walk_map=walk_map)
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    monkeypatch.setattr(CmtsOperation, "listServiceGroups", lambda self: _groups())

    topology = asyncio.run(operation.getServiceGroupTopology())

    assert len(topology) == 1
    entry = topology[0]
    assert int(entry.if_index) == 1049
    assert int(entry.md_ds_sg_id) == 6
    assert int(entry.md_us_sg_id) == 2
    assert int(entry.ds_ch_set_id) == 12
    assert int(entry.us_ch_set_id) == 9
    assert entry.ds_channels == [1, 2]
    assert entry.us_channels == [3, 4]


def test_get_md_cm_sg_id_from_node_name_ds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ds_entries() -> list[tuple[object, object, MdCmSgId]]:
        return [(0, "NODE-1", MdCmSgId(6))]

    async def _us_entries() -> list[tuple[object, object, MdCmSgId]]:
        return []

    monkeypatch.setattr(
        CmtsOperation,
        "getDocsIf3MdNodeStatusMdDsSgId",
        lambda self: _ds_entries(),
    )
    monkeypatch.setattr(
        CmtsOperation,
        "getDocsIf3MdNodeStatusMdUsSgId",
        lambda self: _us_entries(),
    )

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(object(), object()),
    )
    exists, sg_id = asyncio.run(operation.getMdCmSgIdFromNodeName("NODE-1"))

    assert bool(exists) is True
    assert sg_id == MdCmSgId(6)


def test_get_md_cm_sg_id_from_node_name_us(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ds_entries() -> list[tuple[object, object, MdCmSgId]]:
        return []

    async def _us_entries() -> list[tuple[object, object, MdCmSgId]]:
        return [(0, "NODE-2", MdCmSgId(10))]

    monkeypatch.setattr(
        CmtsOperation,
        "getDocsIf3MdNodeStatusMdDsSgId",
        lambda self: _ds_entries(),
    )
    monkeypatch.setattr(
        CmtsOperation,
        "getDocsIf3MdNodeStatusMdUsSgId",
        lambda self: _us_entries(),
    )

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(object(), object()),
    )
    exists, sg_id = asyncio.run(operation.getMdCmSgIdFromNodeName("NODE-2"))

    assert bool(exists) is True
    assert sg_id == MdCmSgId(10)


def test_get_md_cm_sg_id_from_node_name_requires_str() -> None:
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(object(), object()),
    )

    with pytest.raises(TypeError, match=r"node_name must be NodeName or str"):
        asyncio.run(operation.getMdCmSgIdFromNodeName(123))  # type: ignore[arg-type]


def test_get_cm_reg_sg_id_from_node_name(monkeypatch: pytest.MonkeyPatch) -> None:
    base_oid = Snmp_v2c.resolve_oid("docsIf3MdNodeStatusMdDsSgId")
    base = [int(part) for part in base_oid.strip(".").split(".")]
    entries = [base + [1049, 4, 70, 78, 45, 49, 3147266]]
    varbinds = [(_DummyOid(entries[0]), _DummyValue("6"))]

    snmp = _DummySnmpMapping({"docsIf3MdNodeStatusMdDsSgId": varbinds})
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    exists, sg_id = asyncio.run(operation.getCmRegStatusSgIdFromNodeName("FN-1"))

    assert bool(exists) is True
    assert sg_id == CmRegSgId(3147266)


def test_get_cm_reg_sg_id_from_ds_sg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    base_oid = Snmp_v2c.resolve_oid("docsIf3MdNodeStatusMdDsSgId")
    base = [int(part) for part in base_oid.strip(".").split(".")]
    entries = [base + [1050, 4, 70, 78, 45, 50, 3213825]]
    varbinds = [(_DummyOid(entries[0]), _DummyValue("10"))]

    snmp = _DummySnmpMapping({"docsIf3MdNodeStatusMdDsSgId": varbinds})
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=snmp,
    )

    exists, sg_id = asyncio.run(operation.getCmRegStatusSgIdFromDsSgId(MdCmSgId(10)))

    assert bool(exists) is True
    assert sg_id == CmRegSgId(3213825)


def test_get_cm_reg_sg_id_requires_int() -> None:
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(object(), object()),
    )

    with pytest.raises(TypeError, match=r"ds_sg_id must be MdCmSgId or int"):
        asyncio.run(operation.getCmRegStatusSgIdFromDsSgId("10"))  # type: ignore[arg-type]


def test_get_docsif3_cmts_cm_reg_status_mac_addr(monkeypatch: pytest.MonkeyPatch) -> None:
    indices = [10, 11]
    values = ["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"]
    mac_result = object()

    def _extract_last_oid_index(_: object) -> list[int]:
        return indices

    def _snmp_get_result_value(_: object) -> list[str]:
        return values

    def _snmp_get_result_bytes(_: object) -> list[bytes]:
        return [bytes.fromhex(value.replace(":", "")) for value in values]

    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", _extract_last_oid_index)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_value", _snmp_get_result_value)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_bytes", _snmp_get_result_bytes)

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(mac_result, object()),
    )
    results = asyncio.run(operation.getDocsIf3CmtsCmRegStatusMacAddr())

    assert len(results) == 2
    assert int(results[0][0]) == 10
    assert str(results[0][1]) == "aa:bb:cc:dd:ee:ff"


def test_get_docsif3_cmts_cm_reg_status_sg_id_via_mac(monkeypatch: pytest.MonkeyPatch) -> None:
    mac_result = object()
    sg_result = object()
    indices = [5, 6]
    mac_values = ["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"]
    sg_values = ["200", "300"]

    def _extract_last_oid_index(result: object) -> list[int]:
        if result is mac_result:
            return indices
        if result is sg_result:
            return indices
        return []

    def _snmp_get_result_value(result: object) -> list[str]:
        if result is mac_result:
            return mac_values
        if result is sg_result:
            return sg_values
        return []

    def _snmp_get_result_bytes(result: object) -> list[bytes]:
        if result is mac_result:
            return [bytes.fromhex(value.replace(":", "")) for value in mac_values]
        return []

    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", _extract_last_oid_index)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_value", _snmp_get_result_value)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_bytes", _snmp_get_result_bytes)

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(mac_result, sg_result),
    )

    mac = MacAddress("aa:bb:cc:dd:ee:ff")
    exists, sg_id = asyncio.run(
        operation.getdocsIf3CmtsCmRegStatusMdCmSgIdViaMacAddress(mac)
    )

    assert bool(exists) is True
    assert sg_id == MdCmSgId(200)


def test_get_docsif3_cmts_cm_reg_status_sg_id_via_mac_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mac_result = object()
    sg_result = object()
    indices = [5]
    mac_values = ["11:22:33:44:55:66"]
    sg_values = ["200"]

    def _extract_last_oid_index(result: object) -> list[int]:
        if result is mac_result:
            return indices
        if result is sg_result:
            return indices
        return []

    def _snmp_get_result_value(result: object) -> list[str]:
        if result is mac_result:
            return mac_values
        if result is sg_result:
            return sg_values
        return []

    def _snmp_get_result_bytes(result: object) -> list[bytes]:
        if result is mac_result:
            return [bytes.fromhex(value.replace(":", "")) for value in mac_values]
        return []

    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", _extract_last_oid_index)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_value", _snmp_get_result_value)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_bytes", _snmp_get_result_bytes)

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(mac_result, sg_result),
    )

    mac = MacAddress("aa:bb:cc:dd:ee:ff")
    exists, sg_id = asyncio.run(
        operation.getdocsIf3CmtsCmRegStatusMdCmSgIdViaMacAddress(mac)
    )

    assert bool(exists) is False
    assert sg_id == MdCmSgId(0)


def test_get_all_register_cm_filters_indices(monkeypatch: pytest.MonkeyPatch) -> None:
    sg_result = object()
    indices = [1001, 1002, 1003]
    values = ["7", "9", "7"]
    captured: dict[str, list[int]] = {}

    def _extract_last_oid_index(_: object) -> list[int]:
        return indices

    def _snmp_get_result_value(_: object) -> list[str]:
        return values

    async def _get_entries(_: object, entry_indices: list[int]) -> list[DocsIf3CmtsCmRegStatusEntry]:
        captured["indices"] = entry_indices
        return [DocsIf3CmtsCmRegStatusEntry()]

    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", _extract_last_oid_index)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_value", _snmp_get_result_value)
    monkeypatch.setattr(DocsIf3CmtsCmRegStatusIdEntry, "get_entries", _get_entries)

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(sg_result, object()),
    )

    results = asyncio.run(operation.getAllRegisterCm(MdCmSgId(7)))

    assert captured["indices"] == [1001, 1003]
    assert len(results) == 1


def test_get_all_register_cm_requires_mdcm_sg_id() -> None:
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmp(object(), object()),
    )

    with pytest.raises(TypeError, match=r"serving_group_id must be MdCmSgId"):
        asyncio.run(operation.getAllRegisterCm("7"))  # type: ignore[arg-type]


class _DummySnmpMacInet:
    def __init__(self, sg_result: object, get_map: dict[str, str]) -> None:
        self._sg_result = sg_result
        self._get_map = get_map

    async def walk(self, oid: str) -> object | None:
        if oid == "docsIf3CmtsCmRegStatusMdCmSgId":
            return self._sg_result
        return []

    async def get(self, oid: str) -> object | None:
        return self._get_map.get(oid, "")


class _DummySnmpMacInetByMac:
    def __init__(self, mac_result: object, get_map: dict[str, str]) -> None:
        self._mac_result = mac_result
        self._get_map = get_map

    async def walk(self, oid: str) -> object | None:
        if oid == "docsIf3CmtsCmRegStatusMacAddr":
            return self._mac_result
        return []

    async def get(self, oid: str) -> object | None:
        return self._get_map.get(oid, "")


def test_get_all_register_cm_mac_inet_address(monkeypatch: pytest.MonkeyPatch) -> None:
    sg_result = object()
    indices = [1001, 1002]
    values = ["7", "9"]
    get_map = {
        "docsIf3CmtsCmRegStatusMacAddr.1001": "0x001122334455",
        "docsIf3CmtsCmRegStatusIPv4Addr.1001": "192.168.0.10",
        "docsIf3CmtsCmRegStatusIPv6Addr.1001": "2001:db8::1",
        "docsIf3CmtsCmRegStatusIPv6LinkLocal.1001": "fe80::1",
    }

    def _extract_last_oid_index(_: object) -> list[int]:
        return indices

    def _snmp_get_result_value(_: object) -> list[str]:
        return values

    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", _extract_last_oid_index)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_value", _snmp_get_result_value)
    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmpMacInet(sg_result, get_map),
    )

    results = asyncio.run(operation.getAllRegisterCmMacInetAddress(MdCmSgId(7)))

    assert len(results) == 1
    entry: RegisterCmMacInetAddress = results[0]
    assert int(entry[0]) == 1001
    assert entry[1] == "00:11:22:33:44:55"
    assert entry[2] == "192.168.0.10"
    assert entry[3] == "2001:db8::1"
    assert entry[4] == "fe80::1"


def test_get_all_register_cm_mac_inet_address_requires_mdcm_sg_id() -> None:
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmpMacInet(object(), {}),
    )

    with pytest.raises(TypeError, match=r"serving_group_id must be MdCmSgId"):
        asyncio.run(operation.getAllRegisterCmMacInetAddress("7"))  # type: ignore[arg-type]


def test_get_cm_inet_address_by_mac(monkeypatch: pytest.MonkeyPatch) -> None:
    mac_result = object()
    indices = [1001]
    mac_values = ["aa:bb:cc:dd:ee:ff"]
    get_map = {
        "docsIf3CmtsCmRegStatusIPv4Addr.1001": "192.168.0.10",
        "docsIf3CmtsCmRegStatusIPv6Addr.1001": "2001:db8::1",
        "docsIf3CmtsCmRegStatusIPv6LinkLocal.1001": "fe80::1",
    }

    def _extract_last_oid_index(_: object) -> list[int]:
        return indices

    def _snmp_get_result_bytes(_: object) -> list[bytes]:
        return [bytes.fromhex(mac_values[0].replace(":", ""))]

    monkeypatch.setattr(Snmp_v2c, "extract_last_oid_index", _extract_last_oid_index)
    monkeypatch.setattr(Snmp_v2c, "snmp_get_result_bytes", _snmp_get_result_bytes)
    monkeypatch.setattr(Snmp_v2c, "get_result_value", lambda raw: raw)

    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmpMacInetByMac(mac_result, get_map),
    )

    exists, inet_tuple = asyncio.run(
        operation.getCmInetAddress(MacAddress(mac_values[0]))
    )

    assert bool(exists) is True
    assert isinstance(inet_tuple, tuple)
    assert inet_tuple == ("192.168.0.10", "2001:db8::1", "fe80::1")


def test_get_cm_inet_address_requires_mac() -> None:
    operation = CmtsOperation(
        inet=Inet("192.168.0.100"),
        write_community="public",
        snmp=_DummySnmpMacInetByMac(object(), {}),
    )

    with pytest.raises(TypeError, match=r"mac must be MacAddress"):
        asyncio.run(operation.getCmInetAddress("aa:bb:cc:dd:ee:ff"))  # type: ignore[arg-type]

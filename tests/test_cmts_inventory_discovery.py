# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio

from pypnm.lib.types import HostNameStr, SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.docsis.data_type.cmts_cm_reg_status_entry import (
    DocsIf3CmtsCmRegStatusEntry,
)
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.types import (
    ChSetId,
    CmtsCmRegState,
    MdCmSgId,
)


class _FakeOperation:
    async def listServiceGroups(self) -> list[CmtsServiceGroupModel]:
        return [
            CmtsServiceGroupModel(
                md_cm_sg_id=MdCmSgId(2),
                md_ds_sg_id=0,
                md_us_sg_id=0,
                if_index=0,
                node_name="FN-2",
            ),
            CmtsServiceGroupModel(
                md_cm_sg_id=MdCmSgId(1),
                md_ds_sg_id=0,
                md_us_sg_id=0,
                if_index=0,
                node_name="FN-1",
            ),
        ]

    async def getAllRegisterCm(self, serving_group_id: MdCmSgId) -> list[DocsIf3CmtsCmRegStatusEntry]:
        if int(serving_group_id) == 1:
            return [
                DocsIf3CmtsCmRegStatusEntry(
                    docsIf3CmtsCmRegStatusMacAddr="aa:bb:cc:dd:ee:01",
                    docsIf3CmtsCmRegStatusIPv4Addr="192.168.0.11",
                    docsIf3CmtsCmRegStatusIPv6Addr="",
                    docsIf3CmtsCmRegStatusIPv6LinkLocal="",
                    docsIf3CmtsCmRegStatusValue=CmtsCmRegState(5),
                    docsIf3CmtsCmRegStatusRcsId=ChSetId(10),
                    docsIf3CmtsCmRegStatusTcsId=ChSetId(20),
                ),
                DocsIf3CmtsCmRegStatusEntry(
                    docsIf3CmtsCmRegStatusMacAddr="00:11:22:33:44:55",
                    docsIf3CmtsCmRegStatusIPv4Addr="192.168.0.10",
                    docsIf3CmtsCmRegStatusIPv6Addr="",
                    docsIf3CmtsCmRegStatusIPv6LinkLocal="",
                    docsIf3CmtsCmRegStatusValue=CmtsCmRegState(6),
                    docsIf3CmtsCmRegStatusRcsId=ChSetId(11),
                    docsIf3CmtsCmRegStatusTcsId=ChSetId(21),
                ),
            ]
        return [
            DocsIf3CmtsCmRegStatusEntry(
                docsIf3CmtsCmRegStatusMacAddr="aa:bb:cc:dd:ee:ff",
                docsIf3CmtsCmRegStatusIPv4Addr="",
                docsIf3CmtsCmRegStatusIPv6Addr="",
                docsIf3CmtsCmRegStatusIPv6LinkLocal="",
                docsIf3CmtsCmRegStatusValue=CmtsCmRegState(7),
                docsIf3CmtsCmRegStatusRcsId=ChSetId(12),
                docsIf3CmtsCmRegStatusTcsId=ChSetId(22),
            ),
        ]


def test_discovery_inventory_orders_service_groups_and_cms(monkeypatch: object) -> None:
    service = CmtsInventoryDiscoveryService(
        cmts_hostname=HostNameStr("192.168.0.100"),
        read_community=SnmpReadCommunity("public"),
        write_community=SnmpWriteCommunity(""),
        port=161,
    )

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService._build_operation",
        lambda self: _FakeOperation(),
    )

    result = asyncio.run(service.discover_inventory())
    assert isinstance(result, InventoryDiscoveryResultModel)
    assert [int(sg_id) for sg_id in result.discovered_sg_ids] == [1, 2]
    assert [int(entry.sg_id) for entry in result.per_sg] == [1, 2]

    sg_1 = result.per_sg[0]
    assert sg_1.cm_count == 2
    assert [str(cm.mac) for cm in sg_1.cms] == [
        "00:11:22:33:44:55",
        "aa:bb:cc:dd:ee:01",
    ]
    assert int(sg_1.cms[0].ds_channel_set) == 11
    assert int(sg_1.cms[0].us_channel_set) == 21
    assert int(sg_1.cms[0].registration_status) == 6

    sg_2 = result.per_sg[1]
    assert sg_2.cm_count == 1
    assert str(sg_2.cms[0].mac) == "aa:bb:cc:dd:ee:ff"
    assert int(sg_2.cms[0].ds_channel_set) == 12


def test_build_operation_uses_write_community_fallback(monkeypatch: object) -> None:
    captured: dict[str, str] = {}

    class _FakeCmtsOperation:
        def __init__(self, inet: object, write_community: str, port: int) -> None:
            captured["write_community"] = write_community

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsOperation",
        _FakeCmtsOperation,
    )

    service = CmtsInventoryDiscoveryService(
        cmts_hostname=HostNameStr("192.168.0.100"),
        read_community=SnmpReadCommunity("read"),
        write_community=SnmpWriteCommunity(""),
        port=161,
    )
    service._build_operation()
    assert captured["write_community"] == "read"

    service = CmtsInventoryDiscoveryService(
        cmts_hostname=HostNameStr("192.168.0.100"),
        read_community=SnmpReadCommunity("read"),
        write_community=SnmpWriteCommunity("write"),
        port=161,
    )
    service._build_operation()
    assert captured["write_community"] == "write"

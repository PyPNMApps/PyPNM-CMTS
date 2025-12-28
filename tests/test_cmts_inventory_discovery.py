# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio

from pypnm.lib.types import (
    HostNameStr,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    SnmpReadCommunity,
)

from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.lib.types import (
    CableModemIndex,
    IPv6LinkLocalStr,
    MdCmSgId,
    RegisterCmMacInetAddress,
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

    async def getAllRegisterCmMacInetAddress(
        self,
        serving_group_id: MdCmSgId,
    ) -> list[RegisterCmMacInetAddress]:
        if int(serving_group_id) == 1:
            return [
                (
                    CableModemIndex(1),
                    MacAddressStr("ff:ff:ff:ff:ff:ff"),
                    IPv4Str("192.168.0.11"),
                    IPv6Str(""),
                    IPv6LinkLocalStr(IPv6Str("")),
                ),
                (
                    CableModemIndex(2),
                    MacAddressStr("00:11:22:33:44:55"),
                    IPv4Str("192.168.0.10"),
                    IPv6Str(""),
                    IPv6LinkLocalStr(IPv6Str("")),
                ),
            ]
        return [
            (
                CableModemIndex(3),
                MacAddressStr("aa:bb:cc:dd:ee:ff"),
                IPv4Str(""),
                IPv6Str(""),
                IPv6LinkLocalStr(IPv6Str("")),
            ),
        ]


def test_discovery_inventory_orders_service_groups_and_cms(monkeypatch: object) -> None:
    service = CmtsInventoryDiscoveryService(
        cmts_hostname=HostNameStr("192.168.0.100"),
        community=SnmpReadCommunity("public"),
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
        "ff:ff:ff:ff:ff:ff",
    ]

    sg_2 = result.per_sg[1]
    assert sg_2.cm_count == 1
    assert str(sg_2.cms[0].mac) == "aa:bb:cc:dd:ee:ff"

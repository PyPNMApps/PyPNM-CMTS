# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import ChannelId, InterfaceIndex

from pypnm_cmts.api.routes.system.schemas import CmtsServiceGroupTopologyRequest
from pypnm_cmts.api.routes.system.service import SystemCmtsSnmpService
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.lib.types import ChSetId, MdCmSgId, MdDsSgId, MdUsSgId


def test_service_group_topology_endpoint(monkeypatch: object) -> None:
    class _DummyOperation:
        async def getServiceGroupTopology(self) -> list[CmtsServiceGroupTopologyModel]:
            return [
                CmtsServiceGroupTopologyModel(
                    if_index=InterfaceIndex(1049),
                    node_name="NODE-1",
                    md_cm_sg_id=MdCmSgId(3147266),
                    md_ds_sg_id=MdDsSgId(6),
                    md_us_sg_id=MdUsSgId(2),
                    ds_exists=True,
                    us_exists=True,
                    ds_ch_set_id=ChSetId(12),
                    us_ch_set_id=ChSetId(9),
                    ds_channels=[ChannelId(1), ChannelId(2)],
                    us_channels=[ChannelId(3), ChannelId(4)],
                )
            ]

    monkeypatch.setattr(
        "pypnm_cmts.api.routes.system.service.CmtsOperation",
        lambda inet, write_community, port: _DummyOperation(),
    )

    request = CmtsServiceGroupTopologyRequest(
        cmts={"hostname": "192.168.0.100"},
        snmp={"snmp_v2c": {"community": "public"}},
    )

    response = asyncio.run(
        SystemCmtsSnmpService.get_service_group_topology(request)
    )

    assert response.status == ServiceStatusCode.SUCCESS
    assert int(response.results[0].md_ds_sg_id) == 6
    assert response.results[0].ds_channels == [ChannelId(1), ChannelId(2)]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet
from pypnm.lib.types import ChannelId, InterfaceIndex

from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.examples.cli.get_service_group_topology import (
    ServiceGroupTopologyCli,
)
from pypnm_cmts.lib.types import ChSetId, MdCmSgId, MdDsSgId, MdUsSgId


def test_cli_parser_required_args() -> None:
    parser = ServiceGroupTopologyCli.build_parser()
    args = parser.parse_args(
        ["--cmts-hostname", "192.168.0.100", "--cmts-community", "public"]
    )

    assert args.cmts_hostname == "192.168.0.100"
    assert args.cmts_community == "public"
    assert args.text is False


def test_fetch_topology(monkeypatch: pytest.MonkeyPatch) -> None:
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
        "pypnm_cmts.examples.cli.get_service_group_topology.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    entries = asyncio.run(
        ServiceGroupTopologyCli.fetch_topology(Inet("192.168.0.100"), "public")
    )

    assert len(entries) == 1
    assert int(entries[0].ds_ch_set_id) == 12


def test_render_output_json() -> None:
    entries = [
        CmtsServiceGroupTopologyModel(
            if_index=InterfaceIndex(1049),
            node_name="NODE-1",
            md_cm_sg_id=MdCmSgId(3147266),
            md_ds_sg_id=MdDsSgId(6),
            md_us_sg_id=MdUsSgId(2),
            ds_exists=True,
            us_exists=False,
            ds_ch_set_id=ChSetId(12),
            us_ch_set_id=ChSetId(0),
            ds_channels=[ChannelId(1)],
            us_channels=[],
        )
    ]

    output = ServiceGroupTopologyCli.render_output(entries, False)

    payload = json.loads(output)
    assert payload["entries"][0]["md_ds_sg_id"] == 6
    assert payload["entries"][0]["ds_channels"] == [1]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet

from pypnm_cmts.examples.cli.get_cm_reg_sg_id_from_ds_sg_id import (
    CmRegSgIdFromDsSgIdCli,
)
from pypnm_cmts.examples.cli.get_cm_reg_sg_id_from_node_name import (
    CmRegSgIdFromNodeNameCli,
)
from pypnm_cmts.lib.types import CmRegSgId, MdCmSgId


def test_fetch_cm_reg_sg_id_from_node_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyOperation:
        async def getCmRegStatusSgIdFromNodeName(
            self, node_name: str
        ) -> tuple[bool, CmRegSgId]:
            return (True, CmRegSgId(3147266))

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.get_cm_reg_sg_id_from_node_name.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    exists, sg_id = asyncio.run(
        CmRegSgIdFromNodeNameCli.fetch_sg_id(
            Inet("192.168.0.100"), "public", "FN-1"
        )
    )

    assert bool(exists) is True
    assert sg_id == CmRegSgId(3147266)


def test_fetch_cm_reg_sg_id_from_ds_sg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyOperation:
        async def getCmRegStatusSgIdFromDsSgId(
            self, ds_sg_id: MdCmSgId
        ) -> tuple[bool, CmRegSgId]:
            return (True, CmRegSgId(3213825))

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.get_cm_reg_sg_id_from_ds_sg_id.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    exists, sg_id = asyncio.run(
        CmRegSgIdFromDsSgIdCli.fetch_sg_id(
            Inet("192.168.0.100"), "public", MdCmSgId(10)
        )
    )

    assert bool(exists) is True
    assert sg_id == CmRegSgId(3213825)


def test_render_output_node_name_json() -> None:
    output = CmRegSgIdFromNodeNameCli.render_output("FN-1", True, CmRegSgId(3147266), False)

    data = json.loads(output)
    assert data["cm_reg_sg_id"] == 3147266


def test_render_output_ds_sg_id_json() -> None:
    output = CmRegSgIdFromDsSgIdCli.render_output(MdCmSgId(6), True, CmRegSgId(3147266), False)

    data = json.loads(output)
    assert data["ds_sg_id"] == 6

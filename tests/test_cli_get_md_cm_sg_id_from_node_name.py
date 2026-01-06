# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet

from pypnm_cmts.examples.cli.get_md_cm_sg_id_from_node_name import (
    MdCmSgIdFromNodeNameCli,
)
from pypnm_cmts.lib.types import MdCmSgId


def test_fetch_sg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyOperation:
        async def getMdCmSgIdFromNodeName(self, node_name: str) -> tuple[bool, MdCmSgId]:
            return (True, MdCmSgId(6))

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.get_md_cm_sg_id_from_node_name.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    exists, sg_id = asyncio.run(
        MdCmSgIdFromNodeNameCli.fetch_sg_id(
            Inet("192.168.0.100"), "public", "FN-1"
        )
    )

    assert bool(exists) is True
    assert sg_id == MdCmSgId(6)


def test_render_output_json() -> None:
    output = MdCmSgIdFromNodeNameCli.render_output("FN-1", True, MdCmSgId(6), False)

    data = json.loads(output)
    assert data["node_name"] == "FN-1"
    assert data["md_cm_sg_id"] == 6

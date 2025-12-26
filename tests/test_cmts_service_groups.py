# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio

from pypnm.lib.inet import Inet

from pypnm_cmts.docsis.cmts_operation import CmtsOperation


class _DummySnmp:
    def __init__(self, walk_map: dict[str, list[tuple[tuple[int, ...], object]]]) -> None:
        self._walk_map = walk_map

    async def walk(self, oid: str) -> list[tuple[tuple[int, ...], object]]:
        return self._walk_map.get(oid, [])

    async def get(self, oid: str) -> object | None:
        return None


def test_list_service_groups_merges_ds_and_us(monkeypatch: object) -> None:
    async def _run() -> list[tuple[int, str, int, int, int]]:
        ds_base = (1, 3, 6, 1, 4, 1, 4491, 2, 1, 20, 1, 12, 1, 3)
        us_base = (1, 3, 6, 1, 4, 1, 4491, 2, 1, 20, 1, 12, 1, 4)

        node = "NODEA"
        node_bytes = tuple(node.encode("utf-8"))
        if_index = 2
        md_cm_sg_id = 7

        suffix = (if_index, len(node_bytes), *node_bytes, md_cm_sg_id)

        ds_oid = ds_base + suffix
        us_oid = us_base + suffix

        dummy = _DummySnmp(
            {
                "docsIf3MdNodeStatusMdDsSgId": [(ds_oid, 100)],
                "docsIf3MdNodeStatusMdUsSgId": [(us_oid, 200)],
            }
        )

        monkeypatch.setattr(
            "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.resolve_oid",
            lambda name: ".".join(str(x) for x in ds_base) if name == "docsIf3MdNodeStatusMdDsSgId" else ".".join(str(x) for x in us_base),
        )
        monkeypatch.setattr(
            "pypnm_cmts.docsis.cmts_operation.Snmp_v2c.snmp_get_result_value",
            lambda walk_results: [r[1] for r in walk_results],
        )

        op = CmtsOperation(inet=Inet("192.168.0.100"), write_community="public", snmp=dummy)
        groups = await op.listServiceGroups()

        return [
            (
                int(g.if_index),
                str(g.node_name),
                int(g.md_cm_sg_id),
                int(g.md_ds_sg_id),
                int(g.md_us_sg_id),
            )
            for g in groups
        ]

    out = asyncio.run(_run())
    assert out == [(2, "NODEA", 7, 100, 200)]

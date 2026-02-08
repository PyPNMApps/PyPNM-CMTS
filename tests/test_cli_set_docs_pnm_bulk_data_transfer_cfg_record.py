# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet

from pypnm_cmts.examples.cli.set_docs_pnm_bulk_data_transfer_cfg_record import (
    SetDocsPnmBulkDataTransferCfgCli,
)
from pypnm_cmts.lib.constants import DocsPnmBulkDataTransferProtocol
from pypnm_cmts.pnm.data_type.bulk_data_transfer_cfg_entry import (
    DocsPnmBulkDataTransferCfgEntry,
)


def test_cli_parser_required_args() -> None:
    parser = SetDocsPnmBulkDataTransferCfgCli.build_parser()
    args = parser.parse_args(
        [
            "--cmts-hostname",
            "192.168.0.100",
            "--cmts-community-write",
            "private",
            "--index",
            "3",
            "--protocol",
            "https",
        ]
    )

    assert args.cmts_hostname == "192.168.0.100"
    assert args.cmts_community_write == "private"
    assert args.index == 3
    assert args.protocol == DocsPnmBulkDataTransferProtocol.HTTPS


def test_set_record(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _DummyOperation:
        async def setDocsPnmBulkDataTransferCfgRecord(self, index: int, entry: DocsPnmBulkDataTransferCfgEntry) -> bool:
            captured["index"] = index
            captured["entry"] = entry
            return True

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.set_docs_pnm_bulk_data_transfer_cfg_record.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    entry = DocsPnmBulkDataTransferCfgEntry(
        docsPnmBulkDataTransferCfgProtocol=DocsPnmBulkDataTransferProtocol.TFTP,
        docsPnmBulkDataTransferCfgLocalStore=False,
    )
    result = asyncio.run(
        SetDocsPnmBulkDataTransferCfgCli.set_record(Inet("192.168.0.100"), "private", 3, entry)
    )

    assert result is True
    assert captured["index"] == 3
    assert isinstance(captured["entry"], DocsPnmBulkDataTransferCfgEntry)


def test_render_output_json() -> None:
    entry = DocsPnmBulkDataTransferCfgEntry(
        docsPnmBulkDataTransferCfgDestHostname="pnm.example.net",
        docsPnmBulkDataTransferCfgProtocol=DocsPnmBulkDataTransferProtocol.HTTP,
    )

    output = SetDocsPnmBulkDataTransferCfgCli.render_output(
        index=3,
        entry=entry,
        success=True,
        as_text=False,
    )
    payload = json.loads(output)
    assert payload["index"] == 3
    assert payload["success"] is True
    assert payload["updates"]["docsPnmBulkDataTransferCfgDestHostname"] == "pnm.example.net"
    assert payload["updates"]["docsPnmBulkDataTransferCfgProtocol"] == 2

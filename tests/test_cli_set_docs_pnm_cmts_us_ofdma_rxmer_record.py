# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet

from pypnm_cmts.examples.cli.set_docs_pnm_cmts_us_ofdma_rxmer_record import (
    SetDocsPnmCmtsUsOfdmaRxMerCli,
)
from pypnm_cmts.pnm.data_type.ofdma_rxmer_entry import DocsPnmCmtsUsOfdmaRxMerEntry


def test_cli_parser_required_args() -> None:
    parser = SetDocsPnmCmtsUsOfdmaRxMerCli.build_parser()
    args = parser.parse_args(
        [
            "--cmts-hostname",
            "192.168.0.100",
            "--cmts-community-write",
            "private",
            "--if-index",
            "10",
            "--enable",
            "true",
        ]
    )

    assert args.cmts_hostname == "192.168.0.100"
    assert args.cmts_community_write == "private"
    assert args.if_index == 10
    assert args.enable is True


def test_set_record(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _DummyOperation:
        async def setDocsPnmCmtsUsOfdmaRxMerRecord(self, index: int, entry: DocsPnmCmtsUsOfdmaRxMerEntry) -> bool:
            captured["index"] = index
            captured["entry"] = entry
            return True

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.set_docs_pnm_cmts_us_ofdma_rxmer_record.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    entry = DocsPnmCmtsUsOfdmaRxMerEntry(docsPnmCmtsUsOfdmaRxMerEnable=True)
    result = asyncio.run(
        SetDocsPnmCmtsUsOfdmaRxMerCli.set_record(Inet("192.168.0.100"), "private", 10, entry)
    )

    assert result is True
    assert captured["index"] == 10
    assert isinstance(captured["entry"], DocsPnmCmtsUsOfdmaRxMerEntry)


def test_render_output_json() -> None:
    entry = DocsPnmCmtsUsOfdmaRxMerEntry(
        docsPnmCmtsUsOfdmaRxMerEnable=True,
        docsPnmCmtsUsOfdmaRxMerNumAvgs=32,
    )

    output = SetDocsPnmCmtsUsOfdmaRxMerCli.render_output(
        index=10,
        entry=entry,
        success=True,
        as_text=False,
    )
    payload = json.loads(output)
    assert payload["if_index"] == 10
    assert payload["success"] is True
    assert payload["updates"]["docsPnmCmtsUsOfdmaRxMerEnable"] is True
    assert payload["updates"]["docsPnmCmtsUsOfdmaRxMerNumAvgs"] == 32

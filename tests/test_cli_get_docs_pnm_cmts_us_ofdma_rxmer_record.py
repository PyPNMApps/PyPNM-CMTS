# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet

from pypnm_cmts.examples.cli.get_docs_pnm_cmts_us_ofdma_rxmer_record import (
    DocsPnmCmtsUsOfdmaRxMerCli,
)
from pypnm_cmts.pnm.data_type.ofdma_rxmer_entry import (
    DocsPnmCmtsUsOfdmaRxMerEntry,
    DocsPnmCmtsUsOfdmaRxMerRecord,
)


def test_cli_parser_required_args() -> None:
    parser = DocsPnmCmtsUsOfdmaRxMerCli.build_parser()
    args = parser.parse_args(
        ["--cmts-hostname", "192.168.0.100", "--cmts-community", "public"]
    )

    assert args.cmts_hostname == "192.168.0.100"
    assert args.cmts_community == "public"
    assert args.text is False


def test_fetch_records(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = [
        DocsPnmCmtsUsOfdmaRxMerRecord(
            index=42,
            entry=DocsPnmCmtsUsOfdmaRxMerEntry(
                docsPnmCmtsUsOfdmaRxMerEnable=True,
                docsPnmCmtsUsOfdmaRxMerNumAvgs=25,
            ),
        )
    ]

    class _DummyOperation:
        async def getDocsPnmCmtsUsOfdmaRxMerRecord(self) -> list[DocsPnmCmtsUsOfdmaRxMerRecord]:
            return expected

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.get_docs_pnm_cmts_us_ofdma_rxmer_record.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    entries = asyncio.run(
        DocsPnmCmtsUsOfdmaRxMerCli.fetch_records(Inet("192.168.0.100"), "public")
    )
    assert entries == expected


def test_render_output_json() -> None:
    records = [
        DocsPnmCmtsUsOfdmaRxMerRecord(
            index=42,
            entry=DocsPnmCmtsUsOfdmaRxMerEntry(
                docsPnmCmtsUsOfdmaRxMerEnable=True,
                docsPnmCmtsUsOfdmaRxMerNumAvgs=25,
            ),
        )
    ]

    output = DocsPnmCmtsUsOfdmaRxMerCli.render_output(records, False)
    payload = json.loads(output)
    assert payload["entries"][0]["index"] == 42
    assert payload["entries"][0]["entry"]["docsPnmCmtsUsOfdmaRxMerEnable"] is True
    assert payload["entries"][0]["entry"]["docsPnmCmtsUsOfdmaRxMerNumAvgs"] == 25

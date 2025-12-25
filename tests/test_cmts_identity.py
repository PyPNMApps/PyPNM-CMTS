# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio

import pytest
from pypnm.lib.inet import Inet

from pypnm_cmts.docsis.cmts import Cmts
from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class _DummySnmp:
    async def get(self, oid: str) -> object | None:
        return None


def test_cmts_operation_invalid_inet_raises() -> None:
    with pytest.raises(TypeError, match=r"inet must be Inet"):
        CmtsOperation(inet="invalid", write_community="public")  # type: ignore[arg-type]


def test_cmts_hostname_resolution_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _resolve(_: object) -> list[str]:
        return []

    monkeypatch.setattr("pypnm_cmts.docsis.cmts.HostEndpoint.resolve", _resolve)

    with pytest.raises(ValueError, match=r"Hostname resolution failed"):
        Cmts(hostname="cmts-bad", inet=None)  # type: ignore[arg-type]


def test_cmts_sysdescr_failure_returns_empty() -> None:
    async def _run() -> CmtsSysDescrModel:
        inet = Inet("192.168.0.100")
        operation = CmtsOperation(inet=inet, write_community="public", snmp=_DummySnmp())
        return await operation.getSysDescr()

    result = asyncio.run(_run())
    assert result.is_empty

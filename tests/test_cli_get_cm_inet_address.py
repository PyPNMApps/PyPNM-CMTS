# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import json

import pytest
from pypnm.lib.inet import Inet
from pypnm.lib.mac_address import MacAddress

from pypnm_cmts.examples.cli.get_cm_inet_address import CmInetAddressCli
from pypnm_cmts.lib.types import MacAddressExist


def test_fetch_inet_address(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyOperation:
        async def getCmInetAddress(
            self, mac: MacAddress
        ) -> tuple[MacAddressExist, tuple[str, str, str]]:
            return (MacAddressExist(True), ("192.168.0.10", "2001:db8::1", "fe80::1"))

    monkeypatch.setattr(
        "pypnm_cmts.examples.cli.get_cm_inet_address.CmtsOperation",
        lambda inet, write_community: _DummyOperation(),
    )

    exists, inet_tuple = asyncio.run(
        CmInetAddressCli.fetch_inet_address(
            Inet("192.168.0.100"),
            "public",
            MacAddress("aa:bb:cc:dd:ee:ff"),
        )
    )

    assert bool(exists) is True
    assert inet_tuple == ("192.168.0.10", "2001:db8::1", "fe80::1")


def test_render_output_with_raw_values() -> None:
    output = CmInetAddressCli.render_output(
        MacAddress("aa:bb:cc:dd:ee:ff"),
        MacAddressExist(True),
        ("192.168.0.10", "2001:db8::1", "fe80::1"),
        False,
        {"mac_index": 1001, "ipv4": "192.168.0.10"},
    )

    data = json.loads(output)
    assert data["raw"]["mac_index"] == 1001

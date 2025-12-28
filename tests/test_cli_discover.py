# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

from pypnm.lib.types import HostNameStr, IPv4Str, IPv6Str, MacAddressStr
from pytest import CaptureFixture

from pypnm_cmts.cli import EXIT_CODE_USAGE, _run_cli
from pypnm_cmts.cmts.discovery_models import (
    InventoryDiscoveryResultModel,
    RegisteredCableModemModel,
    ServiceGroupCableModemInventoryModel,
)
from pypnm_cmts.lib.types import IPv6LinkLocalStr, ServiceGroupId


def test_cli_discover_outputs_json(monkeypatch: object, tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    class _Args:
        command = "discover"
        cmts_hostname = "192.168.0.100"
        community = "public"
        port = 161
        config = ""
        state_dir = str(tmp_path / "coordination")
        text = False

    monkeypatch.setattr(
        "pypnm_cmts.cli._build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )

    fake_result = InventoryDiscoveryResultModel(
        cmts_host=HostNameStr("192.168.0.100"),
        discovered_sg_ids=[ServiceGroupId(1), ServiceGroupId(2)],
        per_sg=[
            ServiceGroupCableModemInventoryModel(
                sg_id=ServiceGroupId(1),
                cm_count=2,
                cms=[
                    RegisteredCableModemModel(
                        mac=MacAddressStr("00:11:22:33:44:55"),
                        ipv4=IPv4Str("192.168.0.10"),
                        ipv6=IPv6Str(""),
                        ipv6_link_local=IPv6LinkLocalStr(IPv6Str("")),
                    ),
                    RegisteredCableModemModel(
                        mac=MacAddressStr("aa:bb:cc:dd:ee:ff"),
                        ipv4=IPv4Str("192.168.0.11"),
                        ipv6=IPv6Str(""),
                        ipv6_link_local=IPv6LinkLocalStr(IPv6Str("")),
                    ),
                ],
            ),
            ServiceGroupCableModemInventoryModel(
                sg_id=ServiceGroupId(2),
                cm_count=1,
                cms=[
                    RegisteredCableModemModel(
                        mac=MacAddressStr("cc:dd:ee:ff:00:11"),
                        ipv4=IPv4Str(""),
                        ipv6=IPv6Str(""),
                        ipv6_link_local=IPv6LinkLocalStr(IPv6Str("")),
                    ),
                ],
            )
        ],
    )

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.run_discovery",
        lambda cmts_hostname, community, port, state_dir=None: fake_result,
    )

    exit_code = _run_cli()
    assert exit_code == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert [int(sg_id) for sg_id in payload["discovered_sg_ids"]] == [1, 2]
    assert [int(entry["sg_id"]) for entry in payload["per_sg"]] == [1, 2]
    assert [cm["mac"] for cm in payload["per_sg"][0]["cms"]] == [
        "00:11:22:33:44:55",
        "aa:bb:cc:dd:ee:ff",
    ]


def test_cli_discover_outputs_text(monkeypatch: object, tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    class _Args:
        command = "discover"
        cmts_hostname = "192.168.0.100"
        community = "public"
        port = 161
        config = ""
        state_dir = str(tmp_path / "coordination")
        text = True

    monkeypatch.setattr(
        "pypnm_cmts.cli._build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )

    fake_result = InventoryDiscoveryResultModel(
        cmts_host=HostNameStr("192.168.0.100"),
        discovered_sg_ids=[ServiceGroupId(1), ServiceGroupId(2)],
        per_sg=[
            ServiceGroupCableModemInventoryModel(
                sg_id=ServiceGroupId(1),
                cm_count=1,
                cms=[
                    RegisteredCableModemModel(
                        mac=MacAddressStr("aa:bb:cc:dd:ee:ff"),
                        ipv4=IPv4Str("192.168.0.10"),
                        ipv6=IPv6Str(""),
                        ipv6_link_local=IPv6LinkLocalStr(IPv6Str("")),
                    ),
                ],
            ),
            ServiceGroupCableModemInventoryModel(
                sg_id=ServiceGroupId(2),
                cm_count=1,
                cms=[
                    RegisteredCableModemModel(
                        mac=MacAddressStr("bb:cc:dd:ee:ff:00"),
                        ipv4=IPv4Str(""),
                        ipv6=IPv6Str(""),
                        ipv6_link_local=IPv6LinkLocalStr(IPv6Str("")),
                    ),
                ],
            ),
        ],
    )

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.run_discovery",
        lambda cmts_hostname, community, port, state_dir=None: fake_result,
    )

    exit_code = _run_cli()
    assert exit_code == 0

    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip() != ""]
    assert lines[0] == "cmts_host=192.168.0.100"
    assert lines[1].startswith("sg_id=1 ")
    assert lines[2].startswith("  mac=aa:bb:cc:dd:ee:ff")
    assert lines[3].startswith("sg_id=2 ")


def test_cli_discover_requires_hostname(monkeypatch: object) -> None:
    class _Args:
        command = "discover"
        cmts_hostname = ""
        community = ""
        port = 161
        config = ""
        state_dir = ""
        text = False

    monkeypatch.setattr(
        "pypnm_cmts.cli._build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )

    exit_code = _run_cli()
    assert exit_code == EXIT_CODE_USAGE

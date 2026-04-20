# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest

import pypnm_cmts.cli as cli_module


@pytest.mark.unit
def test_current_launch_command_prefers_active_python_for_wrapper_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_module.sys,
        "orig_argv",
        [
            "/usr/bin/python3.10",
            "/home/dev01/Projects/PyPNM-CMTS/.env/bin/pypnm-cmts",
            "serve",
            "--reload",
        ],
        raising=False,
    )
    monkeypatch.setattr(cli_module.sys, "executable", "/home/dev01/Projects/PyPNM-CMTS/.env/bin/python")

    executable, argv = cli_module._current_launch_command()

    assert executable == "/home/dev01/Projects/PyPNM-CMTS/.env/bin/python"
    assert argv == [
        "/home/dev01/Projects/PyPNM-CMTS/.env/bin/pypnm-cmts",
        "serve",
        "--reload",
    ]

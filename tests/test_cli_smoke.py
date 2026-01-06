# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import subprocess
import sys


def _run_help(args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pypnm_cmts", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    return result.stdout


def test_cli_help_smoke() -> None:
    output = _run_help(["--help"])
    assert "PyPNM-CMTS CLI" in output


def test_cli_serve_help_smoke() -> None:
    output = _run_help(["serve", "--help"])
    assert "--host" in output


def test_cli_config_menu_help_smoke() -> None:
    output = _run_help(["config-menu", "--help"])
    assert "config-menu" in output


def test_import_version_exists() -> None:
    import pypnm_cmts

    assert getattr(pypnm_cmts, "__version__", "") != ""

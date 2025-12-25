# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.cli import _run_cli
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings


def test_default_tests_fallback_when_missing() -> None:
    settings = CmtsOrchestratorSettings()
    assert settings.default_tests == ["ds_ofdm_rxmer"]


def test_default_tests_fallback_when_empty() -> None:
    settings = CmtsOrchestratorSettings(default_tests=[])
    assert settings.default_tests == ["ds_ofdm_rxmer"]


def test_worker_mode_requires_sg_id(monkeypatch: object) -> None:
    class _Args:
        command = "run"
        mode = "worker"
        config = ""
        sg_id = ""
        ssl = False
        host = "127.0.0.1"
        port = 8000
        log_level = "info"
        workers = 1
        no_access_log = False
        reload = False
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]

    monkeypatch.setattr(
        "pypnm_cmts.cli._build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )

    exit_code = _run_cli()
    assert exit_code == 2

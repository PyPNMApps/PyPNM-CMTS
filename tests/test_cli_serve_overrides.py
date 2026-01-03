# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os

from pypnm_cmts import cli as cli_module
from pypnm_cmts.config.orchestrator_config import (
    ENV_ADAPTER_HOSTNAME,
    ENV_ADAPTER_READ_COMMUNITY,
    ENV_ADAPTER_WRITE_COMMUNITY,
)

CMTS_HOSTNAME = "cmts.example"
READ_COMMUNITY = "public"
WRITE_COMMUNITY = "private"
HOST = "127.0.0.1"
PORT = 8000


def test_cli_serve_sets_adapter_overrides(monkeypatch: object) -> None:
    monkeypatch.delenv(ENV_ADAPTER_HOSTNAME, raising=False)
    monkeypatch.delenv(ENV_ADAPTER_READ_COMMUNITY, raising=False)
    monkeypatch.delenv(ENV_ADAPTER_WRITE_COMMUNITY, raising=False)

    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = 1
        no_access_log = False
        reload = False
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]
        cmts_hostname = CMTS_HOSTNAME
        read_community = READ_COMMUNITY
        write_community = WRITE_COMMUNITY

    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)

    exit_code = cli_module._run_cli()
    assert exit_code == 0
    assert os.environ[ENV_ADAPTER_HOSTNAME] == CMTS_HOSTNAME
    assert os.environ[ENV_ADAPTER_READ_COMMUNITY] == READ_COMMUNITY
    assert os.environ[ENV_ADAPTER_WRITE_COMMUNITY] == WRITE_COMMUNITY
    assert called["host"] == HOST

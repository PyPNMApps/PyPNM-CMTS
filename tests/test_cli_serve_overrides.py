# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from pypnm_cmts import cli as cli_module
from pypnm_cmts.config import orchestrator_config
from pypnm_cmts.config.orchestrator_config import (
    ENV_ADAPTER_HOSTNAME,
    ENV_ADAPTER_READ_COMMUNITY,
    ENV_ADAPTER_WRITE_COMMUNITY,
)
from pypnm_cmts.config.request_defaults import (
    ENV_CM_SNMPV2C_WRITE_COMMUNITY,
    ENV_CM_TFTP_IPV4,
    ENV_CM_TFTP_IPV6,
)
from pypnm_cmts.config.runtime_flags import (
    ENV_MUTE_PYPNM_ENDPOINTS,
    ENV_MUTE_TAGS,
    ENV_MUTE_TAGS_HARD,
)

CMTS_HOSTNAME = "cmts.example"
READ_COMMUNITY = "public"
WRITE_COMMUNITY = "private"
HOST = "127.0.0.1"
PORT = 8000
CM_SNMPV2C_WRITE_COMMUNITY = "private-write"
CM_TFTP_IPV4 = "192.168.0.100"
CM_TFTP_IPV6 = "::1"


def test_cli_serve_sets_adapter_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_ADAPTER_HOSTNAME, raising=False)
    monkeypatch.delenv(ENV_ADAPTER_READ_COMMUNITY, raising=False)
    monkeypatch.delenv(ENV_ADAPTER_WRITE_COMMUNITY, raising=False)
    monkeypatch.delenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, raising=False)
    monkeypatch.delenv(ENV_CM_TFTP_IPV4, raising=False)
    monkeypatch.delenv(ENV_CM_TFTP_IPV6, raising=False)
    monkeypatch.delenv(ENV_MUTE_PYPNM_ENDPOINTS, raising=False)
    monkeypatch.delenv(ENV_MUTE_TAGS, raising=False)
    monkeypatch.delenv(ENV_MUTE_TAGS_HARD, raising=False)

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
        cm_snmpv2c_write_community = CM_SNMPV2C_WRITE_COMMUNITY
        cm_tftp_ipv4 = CM_TFTP_IPV4
        cm_tftp_ipv6 = CM_TFTP_IPV6
        mute_pypnm_endpoints = False
        mute_tags = ""
        mute_tags_hard = False

    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)
    monkeypatch.setattr(
        orchestrator_config.CmtsOrchestratorSettings,
        "from_system_config",
        staticmethod(lambda: object()),
    )

    exit_code = cli_module._run_cli()
    assert exit_code == 0
    assert os.environ[ENV_ADAPTER_HOSTNAME] == CMTS_HOSTNAME
    assert os.environ[ENV_ADAPTER_READ_COMMUNITY] == READ_COMMUNITY
    assert os.environ[ENV_ADAPTER_WRITE_COMMUNITY] == WRITE_COMMUNITY
    assert os.environ[ENV_CM_SNMPV2C_WRITE_COMMUNITY] == CM_SNMPV2C_WRITE_COMMUNITY
    assert os.environ[ENV_CM_TFTP_IPV4] == CM_TFTP_IPV4
    assert os.environ[ENV_CM_TFTP_IPV6] == CM_TFTP_IPV6
    assert ENV_MUTE_PYPNM_ENDPOINTS not in os.environ
    assert ENV_MUTE_TAGS not in os.environ
    assert ENV_MUTE_TAGS_HARD not in os.environ
    assert called["host"] == HOST


def test_cli_serve_sets_mute_pypnm_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_MUTE_PYPNM_ENDPOINTS, raising=False)

    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        mute_pypnm_endpoints = True
        log_level = "info"
        workers = 1
        no_access_log = False
        reload = False
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        cm_snmpv2c_write_community = ""
        cm_tftp_ipv4 = ""
        cm_tftp_ipv6 = ""
        mute_tags = ""
        mute_tags_hard = False

    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )
    monkeypatch.setattr(cli_module.uvicorn, "run", lambda **_kwargs: None)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)
    monkeypatch.setattr(
        orchestrator_config.CmtsOrchestratorSettings,
        "from_system_config",
        staticmethod(lambda: object()),
    )

    exit_code = cli_module._run_cli()
    assert exit_code == 0
    assert os.environ[ENV_MUTE_PYPNM_ENDPOINTS] == "1"


def test_cli_serve_sets_mute_tags_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_MUTE_TAGS, raising=False)
    monkeypatch.delenv(ENV_MUTE_TAGS_HARD, raising=False)

    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        mute_pypnm_endpoints = False
        mute_tags = "Orchestrator, Operational"
        mute_tags_hard = True
        log_level = "info"
        workers = 1
        no_access_log = False
        reload = False
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        cm_snmpv2c_write_community = ""
        cm_tftp_ipv4 = ""
        cm_tftp_ipv6 = ""

    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )
    monkeypatch.setattr(cli_module.uvicorn, "run", lambda **_kwargs: None)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)
    monkeypatch.setattr(
        orchestrator_config.CmtsOrchestratorSettings,
        "from_system_config",
        staticmethod(lambda: object()),
    )

    exit_code = cli_module._run_cli()
    assert exit_code == 0
    assert os.environ[ENV_MUTE_TAGS] == "Orchestrator, Operational"
    assert os.environ[ENV_MUTE_TAGS_HARD] == "1"


def test_cli_serve_invalid_config_prints_usage(monkeypatch: pytest.MonkeyPatch) -> None:
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
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        cm_snmpv2c_write_community = ""
        cm_tftp_ipv4 = ""
        cm_tftp_ipv6 = ""
        mute_pypnm_endpoints = False
        mute_tags = ""
        mute_tags_hard = False

    class _Model(BaseModel):
        value: int

    try:
        _Model.model_validate({"value": "bad"})
    except ValidationError as exc:
        validation_error = exc

    called: dict[str, object] = {"usage": False}

    def _mark_usage(_parser: object) -> None:
        called["usage"] = True

    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )
    monkeypatch.setattr(cli_module, "_print_serve_usage", _mark_usage)
    monkeypatch.setattr(
        orchestrator_config.CmtsOrchestratorSettings,
        "from_system_config",
        staticmethod(lambda: (_raise_validation_error(validation_error))),
    )
    monkeypatch.setattr(cli_module.uvicorn, "run", lambda **_kwargs: None)

    exit_code = cli_module._run_cli()
    assert exit_code == 2
    assert called["usage"] is True


def test_cli_serve_anchors_pythonpath_to_project_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.chdir(tmp_path)

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
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        cm_snmpv2c_write_community = ""
        cm_tftp_ipv4 = ""
        cm_tftp_ipv6 = ""
        mute_pypnm_endpoints = False
        mute_tags = ""
        mute_tags_hard = False

    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: _Args()})(),
    )
    monkeypatch.setattr(
        orchestrator_config.CmtsOrchestratorSettings,
        "from_system_config",
        staticmethod(lambda: object()),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called["cwd"] = Path.cwd()
        called["pythonpath"] = os.environ.get("PYTHONPATH", "")
        called["cert"] = kwargs.get("ssl_certfile")
        called["key"] = kwargs.get("ssl_keyfile")

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)

    exit_code = cli_module._run_cli()

    project_root = Path(cli_module.__file__).resolve().parents[2]
    assert exit_code == 0
    assert called["cwd"] == tmp_path
    assert called["pythonpath"] == str(project_root / "src")
    assert Path.cwd() == tmp_path


def test_prepare_runtime_paths_for_serve_resolves_relative_user_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYTHONPATH", raising=False)

    class _Args:
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        reload_dirs = ["src", "tools"]

    args = _Args()
    cli_module._prepare_runtime_paths_for_serve(args)

    project_root = Path(cli_module.__file__).resolve().parents[2]
    assert Path.cwd() == tmp_path
    assert args.cert == str((tmp_path / "certs" / "cert.pem").resolve())
    assert args.key == str((tmp_path / "certs" / "key.pem").resolve())
    assert args.reload_dirs == [
        str((tmp_path / "src").resolve()),
        str((tmp_path / "tools").resolve()),
    ]
    assert os.environ["PYTHONPATH"] == str(project_root / "src")


def _raise_validation_error(exc: ValidationError) -> None:
    raise exc

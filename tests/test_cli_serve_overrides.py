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


def _sgw_enabled_settings() -> orchestrator_config.CmtsOrchestratorSettings:
    return orchestrator_config.CmtsOrchestratorSettings.model_validate(
        {
            "adapter": {
                "hostname": CMTS_HOSTNAME,
                "community": READ_COMMUNITY,
                "write_community": "",
                "port": 161,
            },
            "sgw": {"enabled": True},
            "state_dir": "./.data/coordination",
        }
    )


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
        workers = None
        limit_max_requests = None
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
        workers = None
        limit_max_requests = None
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
        workers = None
        limit_max_requests = None
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
        workers = None
        limit_max_requests = None
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
        workers = None
        limit_max_requests = None
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


def test_cli_serve_auto_selects_seeded_worker_profile(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
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
    monkeypatch.setattr(
        cli_module,
        "load_seeded_profile",
        lambda _path: cli_module.WorkerProfile(
            cpu_count=8,
            total_memory_gib=16.0,
            workers=4,
            limit_max_requests=2000,
        ),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)

    exit_code = cli_module._run_cli()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert called["workers"] == 4
    assert called["limit_max_requests"] == 2000
    assert "Auto-selected FastAPI runtime profile" in captured.out


def test_cli_serve_auto_selects_hardware_profile_when_seed_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
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
    monkeypatch.setattr(cli_module, "load_seeded_profile", lambda _path: None)
    monkeypatch.setattr(
        cli_module,
        "detect_worker_profile",
        lambda: cli_module.WorkerProfile(
            cpu_count=8,
            total_memory_gib=32.0,
            workers=4,
            limit_max_requests=2000,
        ),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)

    exit_code = cli_module._run_cli()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert called["workers"] == 4
    assert called["limit_max_requests"] == 2000
    assert "source=hardware_auto" in captured.out


def test_cli_serve_reload_forces_single_worker_even_with_auto_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
        no_access_log = False
        reload = True
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
    monkeypatch.setattr(
        cli_module,
        "detect_worker_profile",
        lambda: cli_module.WorkerProfile(
            cpu_count=8,
            total_memory_gib=32.0,
            workers=4,
            limit_max_requests=2000,
        ),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)

    exit_code = cli_module._run_cli()

    assert exit_code == 0
    assert called["workers"] == cli_module.DEFAULT_WORKERS
    assert called["limit_max_requests"] == 2000


def test_cli_serve_with_runner_forces_single_worker_even_with_auto_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = True
        log_level = "info"
        workers = None
        limit_max_requests = None
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
    monkeypatch.setattr(
        cli_module,
        "detect_worker_profile",
        lambda: cli_module.WorkerProfile(
            cpu_count=8,
            total_memory_gib=32.0,
            workers=4,
            limit_max_requests=2000,
        ),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)

    exit_code = cli_module._run_cli()

    assert exit_code == 0
    assert called["workers"] == cli_module.DEFAULT_WORKERS
    assert called["limit_max_requests"] == 2000


def test_cli_serve_sgw_enabled_forces_single_worker_even_with_auto_profile(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
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
        staticmethod(_sgw_enabled_settings),
    )
    monkeypatch.setattr(
        cli_module,
        "detect_worker_profile",
        lambda: cli_module.WorkerProfile(
            cpu_count=8,
            total_memory_gib=32.0,
            workers=4,
            limit_max_requests=2000,
        ),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)

    exit_code = cli_module._run_cli()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert called["workers"] == cli_module.DEFAULT_WORKERS
    assert called["limit_max_requests"] == 2000
    assert "forcing workers=1" in captured.out


def test_cli_serve_sgw_enabled_forces_single_worker_even_when_explicit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = 4
        limit_max_requests = 2000
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
        staticmethod(_sgw_enabled_settings),
    )

    called: dict[str, object] = {}

    def _fake_run(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)

    exit_code = cli_module._run_cli()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert called["workers"] == cli_module.DEFAULT_WORKERS
    assert called["limit_max_requests"] == 2000
    assert "forcing workers=1" in captured.out


def test_cli_serve_run_background_launches_detached_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
        no_access_log = False
        reload = False
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]
        run_background = True
        background_log_file = "/tmp/pypnm-cmts.log"
        background_pidfile = "/tmp/pypnm-cmts.pid"
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
    monkeypatch.setattr(cli_module.CmtsSystemConfigSettings, "runtime_dir", classmethod(lambda cls: "/tmp/pypnm-cmts-runtime"))

    called: dict[str, object] = {}

    def _fake_launch_background_serve(**kwargs: object) -> int:
        called.update(kwargs)
        return cli_module.SUCCESS_EXIT_CODE

    uvicorn_called = {"value": False}

    def _fake_run(**_kwargs: object) -> None:
        uvicorn_called["value"] = True

    monkeypatch.setattr(cli_module, "launch_background_serve", _fake_launch_background_serve)
    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)

    exit_code = cli_module._run_cli()

    assert exit_code == cli_module.SUCCESS_EXIT_CODE
    assert uvicorn_called["value"] is False
    assert called["module_name"] == "pypnm_cmts.cli"
    assert called["app_slug"] == "pypnm-cmts"
    assert called["runtime_dir"] == "/tmp/pypnm-cmts-runtime"
    assert called["log_file"] == "/tmp/pypnm-cmts.log"
    assert called["pidfile"] == "/tmp/pypnm-cmts.pid"


def test_cli_serve_run_background_rejects_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
        no_access_log = False
        reload = True
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]
        run_background = True
        background_log_file = ""
        background_pidfile = ""
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

    uvicorn_called = {"value": False}

    def _fake_run(**_kwargs: object) -> None:
        uvicorn_called["value"] = True

    monkeypatch.setattr(cli_module.uvicorn, "run", _fake_run)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)

    exit_code = cli_module._run_cli()

    assert exit_code == cli_module.EXIT_CODE_USAGE
    assert uvicorn_called["value"] is False


def test_cli_serve_background_child_rewrites_pidfile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pidfile = tmp_path / "pypnm-cmts.serve.pid"

    class _Args:
        command = "serve"
        host = HOST
        port = PORT
        ssl = False
        cert = "./certs/cert.pem"
        key = "./certs/key.pem"
        with_runner = False
        log_level = "info"
        workers = None
        limit_max_requests = None
        no_access_log = False
        reload = False
        reload_dirs: list[str] = []
        reload_includes: list[str] = ["*.py"]
        reload_excludes: list[str] = ["*.pyc", "*__pycache__*", "*.tmp", "*.log"]
        run_background = False
        background_log_file = ""
        background_pidfile = ""
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
    monkeypatch.setenv(cli_module.BACKGROUND_CHILD_ENV, "1")
    monkeypatch.setenv(cli_module.BACKGROUND_PIDFILE_ENV, str(pidfile))
    monkeypatch.setattr(cli_module.uvicorn, "run", lambda **_kwargs: None)
    monkeypatch.setattr(cli_module, "_print_serve_usage", lambda _parser: None)
    monkeypatch.setattr(cli_module, "_prepare_runtime_paths_for_serve", lambda _args: None)
    monkeypatch.setattr(
        cli_module,
        "detect_worker_profile",
        lambda: cli_module.WorkerProfile(cpu_count=4, total_memory_gib=16.0, workers=2, limit_max_requests=1000),
    )

    exit_code = cli_module._run_cli()

    assert exit_code == cli_module.SUCCESS_EXIT_CODE
    assert pidfile.read_text(encoding="utf-8").strip() == str(os.getpid())

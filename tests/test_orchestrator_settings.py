# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from pypnm_cmts.cli import EXIT_CODE_USAGE, _build_launcher, _build_parser, _run_cli
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.models import CoordinationTickResultModel
from pypnm_cmts.orchestrator.models import OrchestratorRunResultModel


def test_default_tests_fallback_when_missing() -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    assert settings.default_tests == ["ds_ofdm_rxmer"]


def test_default_tests_fallback_when_empty() -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {"default_tests": [], "adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    assert settings.default_tests == ["ds_ofdm_rxmer"]


def test_worker_mode_allows_unbound(monkeypatch: object, tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path, enabled=True)

    class _Args:
        command = "run"
        mode = "worker"
        config = str(config_path)
        sg_id = ""
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds: float | None = None
        leader_ttl_seconds: int | None = None
        lease_ttl_seconds: int | None = None
        state_dir = ""
        election_name = ""
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

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher.run_once",
        lambda self: _build_minimal_run_result(),
    )

    exit_code = _run_cli()
    assert exit_code == 0


def test_orchestrator_settings_invalid_shard_mode_raises() -> None:
    with pytest.raises(ValueError):
        CmtsOrchestratorSettings.model_validate(
            {"shard_mode": "invalid", "adapter": {"hostname": "cmts.example", "community": "public"}}
        )


def test_orchestrator_settings_negative_target_service_groups_raises() -> None:
    with pytest.raises(ValueError):
        CmtsOrchestratorSettings.model_validate(
            {"target_service_groups": -1, "adapter": {"hostname": "cmts.example", "community": "public"}}
        )


def test_orchestrator_settings_negative_worker_cap_raises() -> None:
    with pytest.raises(ValueError):
        CmtsOrchestratorSettings.model_validate(
            {"worker_cap": -1, "adapter": {"hostname": "cmts.example", "community": "public"}}
        )


def test_cli_snmp_port_override_passed_to_launcher(monkeypatch: object) -> None:
    captured: dict[str, int | None] = {}

    class _FakeLauncher:
        def __init__(self, *args: object, adapter_port: int | None = None, **kwargs: object) -> None:
            captured["adapter_port"] = adapter_port

    monkeypatch.setattr("pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher", _FakeLauncher)

    class _Args:
        mode = "standalone"
        config = ""
        sg_id = ""
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds: float | None = None
        leader_ttl_seconds: int | None = None
        lease_ttl_seconds: int | None = None
        state_dir = ""
        election_name = ""
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        snmp_port: int | None = 1161

    _build_launcher(_Args())
    assert captured["adapter_port"] == 1161


def test_cli_snmp_port_omitted_uses_config_default(monkeypatch: object) -> None:
    captured: dict[str, int | None] = {}

    class _FakeLauncher:
        def __init__(self, *args: object, adapter_port: int | None = None, **kwargs: object) -> None:
            captured["adapter_port"] = adapter_port

    monkeypatch.setattr("pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher", _FakeLauncher)

    class _Args:
        mode = "standalone"
        config = ""
        sg_id = ""
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds: float | None = None
        leader_ttl_seconds: int | None = None
        lease_ttl_seconds: int | None = None
        state_dir = ""
        election_name = ""
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        snmp_port: int | None = None

    _build_launcher(_Args())
    assert captured["adapter_port"] is None


def test_cli_cmts_port_alias_parses_into_snmp_port() -> None:
    parser = _build_parser()
    args = parser.parse_args(["run", "--mode", "standalone", "--cmts-port", "1161"])
    assert args.snmp_port == 1161


def test_cli_snmp_port_takes_precedence_over_cmts_port(monkeypatch: object) -> None:
    captured: dict[str, int | None] = {}

    class _FakeLauncher:
        def __init__(self, *args: object, adapter_port: int | None = None, **kwargs: object) -> None:
            captured["adapter_port"] = adapter_port

    monkeypatch.setattr("pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher", _FakeLauncher)
    monkeypatch.setattr(
        sys,
        "argv",
        ["pypnm-cmts", "run", "--mode", "standalone", "--snmp-port", "1161", "--cmts-port", "2000"],
    )
    monkeypatch.setattr("pypnm_cmts.cli._cmts_port_warned", True)

    class _Args:
        mode = "standalone"
        config = ""
        sg_id = ""
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds: float | None = None
        leader_ttl_seconds: int | None = None
        lease_ttl_seconds: int | None = None
        state_dir = ""
        election_name = ""
        cmts_hostname = ""
        read_community = ""
        write_community = ""
        snmp_port: int | None = 2000

    _build_launcher(_Args())
    assert captured["adapter_port"] == 1161


def _write_system_config(path: Path, enabled: bool = True) -> None:
    payload = {
        "CmtsOrchestrator": {
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": enabled},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_minimal_run_result() -> OrchestratorRunResultModel:
    payload = {
        "mode": "standalone",
        "tick_index": 1,
        "run_id": "",
        "lease_held": False,
        "inventory": {
            "sg_ids": [],
            "count": 0,
            "source": "config",
        },
        "coordination_tick": {},
        "coordination_status": {},
        "leader_status": {},
        "target_service_groups": 0,
        "work_results": [],
    }
    return OrchestratorRunResultModel.model_validate(payload)


def test_cli_worker_rejects_non_numeric_sg_id(monkeypatch: object, tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path, enabled=True)

    class _Args:
        command = "run"
        mode = "worker"
        config = str(config_path)
        sg_id = "sg-1"
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds: float | None = None
        leader_ttl_seconds: int | None = None
        lease_ttl_seconds: int | None = None
        state_dir = str(tmp_path / "coordination")
        election_name = ""
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
    assert exit_code == EXIT_CODE_USAGE


def test_cli_worker_rejects_sg_id_not_enabled(monkeypatch: object, tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path, enabled=False)

    class _Args:
        command = "run"
        mode = "worker"
        config = str(config_path)
        sg_id = "1"
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds: float | None = None
        leader_ttl_seconds: int | None = None
        lease_ttl_seconds: int | None = None
        state_dir = str(tmp_path / "coordination")
        election_name = ""
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
    assert exit_code == EXIT_CODE_USAGE


def test_orchestrator_settings_tick_interval_validation_raises() -> None:
    with pytest.raises(ValueError, match="tick_interval_seconds must be less than"):
        CmtsOrchestratorSettings.model_validate(
            {
                "tick_interval_seconds": 10,
                "leader_ttl_seconds": 10,
                "lease_ttl_seconds": 10,
                "adapter": {"hostname": "cmts.example", "community": "public"},
            }
        )


def test_orchestrator_settings_tick_interval_valid() -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {
            "tick_interval_seconds": 1,
            "leader_ttl_seconds": 10,
            "lease_ttl_seconds": 10,
            "adapter": {"hostname": "cmts.example", "community": "public"},
        }
    )
    assert float(settings.tick_interval_seconds) == 1.0


def test_cli_rejects_invalid_tick_interval(monkeypatch: object, tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path, enabled=True)

    class _Args:
        command = "run"
        mode = "standalone"
        config = str(config_path)
        sg_id = ""
        owner_id = ""
        target_service_groups: int | None = None
        shard_mode: str | None = None
        tick_interval_seconds = 10.0
        leader_ttl_seconds = 10
        lease_ttl_seconds = 10
        state_dir = str(tmp_path / "coordination")
        election_name = ""
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
    assert exit_code == EXIT_CODE_USAGE


def test_cli_run_single_tick_accepts_new_flags_calls_run_once(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path, enabled=True)

    class _Args:
        command = "run"
        mode = "standalone"
        config = str(config_path)
        sg_id = ""
        owner_id = "owner-1"
        target_service_groups = 2
        shard_mode = "score"
        tick_interval_seconds = 1.0
        leader_ttl_seconds = 10
        lease_ttl_seconds = 10
        state_dir = str(tmp_path / "coordination")
        election_name = "cmts-test"
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

    called: dict[str, int] = {"run_once": 0}

    def _fake_run_once(self: object) -> OrchestratorRunResultModel:
        called["run_once"] += 1
        return _build_minimal_run_result()

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher.run_once",
        _fake_run_once,
    )

    exit_code = _run_cli()
    assert exit_code == 0
    assert called["run_once"] == 1


def test_cli_run_forever_accepts_new_flags_calls_run_forever(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path, enabled=True)

    class _Args:
        command = "run-forever"
        mode = "standalone"
        config = str(config_path)
        sg_id = ""
        owner_id = "owner-1"
        target_service_groups = 2
        shard_mode = "score"
        tick_interval_seconds = 1.0
        leader_ttl_seconds = 10
        lease_ttl_seconds = 10
        state_dir = str(tmp_path / "coordination")
        election_name = "cmts-test"
        max_ticks: int | None = None
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

    called: dict[str, int] = {"run_forever": 0}

    def _fake_run_forever(
        self: object,
        on_tick: Callable[[OrchestratorRunResultModel], None] | None = None,
        max_ticks: int | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> list[CoordinationTickResultModel]:
        called["run_forever"] += 1
        if on_tick is not None:
            on_tick(_build_minimal_run_result())
        return []

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher.run_forever",
        _fake_run_forever,
    )

    exit_code = _run_cli()
    assert exit_code == 0
    assert called["run_forever"] == 1

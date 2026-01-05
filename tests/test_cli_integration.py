# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SUCCESS_EXIT_CODE = 0
EXIT_CODE_USAGE = 2
CLI_TIMEOUT_SECONDS = 10


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{_repo_root() / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return env


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "pypnm_cmts.cli", *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=_env(),
        text=True,
        capture_output=True,
        timeout=CLI_TIMEOUT_SECONDS,
    )


def _run_package(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "pypnm_cmts", *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=_env(),
        text=True,
        capture_output=True,
        timeout=CLI_TIMEOUT_SECONDS,
    )


def _write_system_config(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "adapter": {
                "hostname": "cmts.example",
                "community": "public",
                "write_community": "",
                "port": 161,
            },
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
            "sgw": {"discovery": {"mode": "static"}},
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_system_config_no_leases(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "adapter": {
                "hostname": "cmts.example",
                "community": "public",
                "write_community": "",
                "port": 161,
            },
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
            ],
            "target_service_groups": 0,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
            "sgw": {"discovery": {"mode": "static"}},
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_system_config_multi(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "adapter": {
                "hostname": "cmts.example",
                "community": "public",
                "write_community": "",
                "port": 161,
            },
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
                {"sg_id": 2, "name": "sg-2", "enabled": True},
                {"sg_id": 3, "name": "sg-3", "enabled": True},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
            "sgw": {"discovery": {"mode": "static"}},
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_help_root() -> None:
    result = _run_cli(["--help"], cwd=_repo_root())
    assert result.returncode == SUCCESS_EXIT_CODE


def test_cli_help_quiet_and_lists_snmp_port() -> None:
    result = _run_cli(["run", "--help"], cwd=_repo_root())
    assert result.returncode == SUCCESS_EXIT_CODE
    assert "--snmp-port" in result.stdout
    assert "PnmFileRetrieval.retrieval_method.methods.tftp.remote_dir" not in result.stderr


def test_cli_help_package_module() -> None:
    result = _run_package(["--help"], cwd=_repo_root())
    assert result.returncode == SUCCESS_EXIT_CODE


def test_cli_help_run() -> None:
    result = _run_cli(["run", "--help"], cwd=_repo_root())
    assert result.returncode == SUCCESS_EXIT_CODE


def test_cli_run_requires_mode() -> None:
    result = _run_cli(["run"], cwd=_repo_root())
    assert result.returncode == EXIT_CODE_USAGE
    assert "the following arguments are required: --mode" in result.stderr


def test_cli_help_run_forever() -> None:
    result = _run_cli(["run-forever", "--help"], cwd=_repo_root())
    assert result.returncode == SUCCESS_EXIT_CODE


def test_cli_help_serve() -> None:
    result = _run_cli(["serve", "--help"], cwd=_repo_root())
    assert result.returncode == SUCCESS_EXIT_CODE


def test_cli_no_command_exits_usage_and_shows_help() -> None:
    result = _run_cli([], cwd=_repo_root())
    assert result.returncode == EXIT_CODE_USAGE
    assert "usage:" in result.stdout


def test_cli_worker_without_sg_id_uses_inventory(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config_no_leases(config_path)

    result = _run_cli(
        [
            "run",
            "--mode",
            "worker",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
        ],
        cwd=_repo_root(),
    )
    assert result.returncode == SUCCESS_EXIT_CODE
    payload = json.loads(result.stdout)
    assert payload["mode"] == "worker"
    assert payload["lease_held"] is False
    assert payload["run_id"] == ""


def test_cli_run_single_tick_outputs_json(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    result = _run_cli(
        [
            "run",
            "--mode",
            "standalone",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
        ],
        cwd=_repo_root(),
    )

    assert result.returncode == SUCCESS_EXIT_CODE
    payload = json.loads(result.stdout)
    assert "mode" in payload
    assert "inventory" in payload


def test_cli_invalid_snmp_port_reports_value(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    result = _run_cli(
        [
            "run",
            "--mode",
            "standalone",
            "--snmp-port",
            "0",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
        ],
        cwd=_repo_root(),
    )

    assert result.returncode == EXIT_CODE_USAGE
    assert "snmp-port must be greater than zero (got 0)" in result.stderr


def test_cli_cmts_port_deprecation_warning(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    result = _run_cli(
        [
            "run",
            "--mode",
            "standalone",
            "--cmts-port",
            "161",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
        ],
        cwd=_repo_root(),
    )

    assert result.returncode == SUCCESS_EXIT_CODE
    assert result.stderr.count("DEPRECATED: --cmts-port is deprecated; use --snmp-port.") == 1


def test_cli_run_forever_outputs_jsonl(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    result = _run_cli(
        [
            "run-forever",
            "--mode",
            "standalone",
            "--max-ticks",
            "2",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
        ],
        cwd=_repo_root(),
    )

    assert result.returncode == SUCCESS_EXIT_CODE
    lines = [line for line in result.stdout.splitlines() if line.strip() != ""]
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert "mode" in payload
        assert "inventory" in payload
        assert "work_results" in payload
        assert "tick_index" in payload
        assert "run_id" in payload
        assert "lease_held" in payload
        assert payload["tick_index"] > 0
        assert payload["run_id"] == ""
        assert payload["lease_held"] is False


def test_cli_run_forever_rejects_negative_max_ticks() -> None:
    result = _run_cli(
        [
            "run-forever",
            "--mode",
            "standalone",
            "--max-ticks",
            "-1",
        ],
        cwd=_repo_root(),
    )
    assert result.returncode == EXIT_CODE_USAGE
    assert "--max-ticks must be non-negative" in result.stderr


def test_cli_run_forever_worker_outputs_work_results(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    result = _run_cli(
        [
            "run-forever",
            "--mode",
            "worker",
            "--sg-id",
            "1",
            "--max-ticks",
            "2",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
        ],
        cwd=_repo_root(),
    )

    assert result.returncode == SUCCESS_EXIT_CODE
    lines = [line for line in result.stdout.splitlines() if line.strip() != ""]
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert "work_results" in payload
        assert len(payload["work_results"]) > 0
        assert payload["tick_index"] > 0
        assert payload["run_id"].startswith("sg1_tick")
        assert payload["lease_held"] is True

    results_dir = state_dir / "results" / "sg_1"
    assert results_dir.exists()
    persisted = list(results_dir.glob("*.json"))
    assert len(persisted) == 2
    for path in persisted:
        assert path.name.startswith("sg1_tick")


def test_cli_run_forever_multi_worker_shared_state_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config_multi(config_path)

    worker_1 = _run_cli(
        [
            "run-forever",
            "--mode",
            "worker",
            "--sg-id",
            "1",
            "--max-ticks",
            "3",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
            "--owner-id",
            "worker-1",
        ],
        cwd=_repo_root(),
    )
    assert worker_1.returncode == SUCCESS_EXIT_CODE
    worker_1_lines = [line for line in worker_1.stdout.splitlines() if line.strip() != ""]
    assert len(worker_1_lines) == 3
    for line in worker_1_lines:
        payload = json.loads(line)
        assert payload["tick_index"] > 0
        assert payload["lease_held"] is True
        assert payload["run_id"].startswith("sg1_tick")

    worker_2 = _run_cli(
        [
            "run-forever",
            "--mode",
            "worker",
            "--sg-id",
            "2",
            "--max-ticks",
            "3",
            "--config",
            str(config_path),
            "--state-dir",
            str(state_dir),
            "--owner-id",
            "worker-2",
        ],
        cwd=_repo_root(),
    )
    assert worker_2.returncode == SUCCESS_EXIT_CODE
    worker_2_lines = [line for line in worker_2.stdout.splitlines() if line.strip() != ""]
    assert len(worker_2_lines) == 3
    for line in worker_2_lines:
        payload = json.loads(line)
        assert payload["tick_index"] > 0
        assert payload["lease_held"] is True
        assert payload["run_id"].startswith("sg2_tick")

    results_sg1 = state_dir / "results" / "sg_1"
    results_sg2 = state_dir / "results" / "sg_2"
    results_sg3 = state_dir / "results" / "sg_3"
    assert results_sg1.exists()
    assert results_sg2.exists()
    assert results_sg3.exists() is False
    persisted_sg1 = list(results_sg1.glob("*.json"))
    persisted_sg2 = list(results_sg2.glob("*.json"))
    assert len(persisted_sg1) == 3
    assert len(persisted_sg2) == 3
    for path in persisted_sg1:
        assert path.name.startswith("sg1_tick")
    for path in persisted_sg2:
        assert path.name.startswith("sg2_tick")

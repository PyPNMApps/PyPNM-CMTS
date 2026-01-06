# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

CLI_SMOKE_TIMEOUT_SECONDS = 30.0
ENV_ADAPTER_HOSTNAME = "PYPNM_CMTS_ADAPTER_HOSTNAME"
ENV_ADAPTER_READ_COMMUNITY = "PYPNM_CMTS_ADAPTER_READ_COMMUNITY"
DEFAULT_CMTS_HOSTNAME = "cmts.example"
DEFAULT_CMTS_READ_COMMUNITY = "public"


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_version(base_url: str, timeout_seconds: float) -> httpx.Response | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/ops/version", timeout=2.0)
        except httpx.RequestError:
            time.sleep(0.1)
            continue

        if response.status_code == 200:
            return response

        time.sleep(0.1)
    return None


def _wait_for_status(base_url: str, timeout_seconds: float) -> dict[str, object] | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/ops/status", timeout=2.0)
        except httpx.RequestError:
            time.sleep(0.1)
            continue

        if response.status_code == 200:
            payload = response.json()
            if not payload.get("pid_records_missing", False):
                return payload

        time.sleep(0.1)
    return None


def test_ops_version_smoke_starts_service() -> None:
    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = dict(os.environ)
    env[ENV_ADAPTER_HOSTNAME] = DEFAULT_CMTS_HOSTNAME
    env[ENV_ADAPTER_READ_COMMUNITY] = DEFAULT_CMTS_READ_COMMUNITY

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pypnm_cmts.cli",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
    )

    try:
        response = _wait_for_version(base_url, timeout_seconds=CLI_SMOKE_TIMEOUT_SECONDS)
        assert response is not None
        payload = response.json()
        assert payload.get("application") == "pypnm-cmts"
        assert "version" in payload
        assert "python_version" in payload
    finally:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)


def test_ops_status_combined_mode_runner_available() -> None:
    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = dict(os.environ)
    env[ENV_ADAPTER_HOSTNAME] = DEFAULT_CMTS_HOSTNAME
    env[ENV_ADAPTER_READ_COMMUNITY] = DEFAULT_CMTS_READ_COMMUNITY

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pypnm_cmts.cli",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
            "--with-runner",
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
    )

    try:
        assert _wait_for_version(base_url, timeout_seconds=CLI_SMOKE_TIMEOUT_SECONDS) is not None
        payload = _wait_for_status(base_url, timeout_seconds=CLI_SMOKE_TIMEOUT_SECONDS)
        assert payload is not None
        assert payload["pid_records_missing"] is False
        controller = payload["controller"]
        assert controller["pidfile_exists"] is True
        assert controller["is_running"] is True
    finally:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)

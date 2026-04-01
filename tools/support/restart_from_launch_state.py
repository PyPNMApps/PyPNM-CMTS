#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

from pypnm_cmts.support.serve_launch_state import (
    read_launch_state,
    resolve_launch_state_path,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restart pypnm-cmts from the last recorded serve launch state.",
    )
    parser.add_argument(
        "--state-path",
        default="",
        help="Optional launch-state file path. Default: configured runtime launch-state path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved restart command and exit.",
    )
    return parser.parse_args()


def _resolve_state_path(value: str) -> Path:
    if value.strip() == "":
        return resolve_launch_state_path()
    return Path(value).expanduser().resolve()


def _looks_like_pypnm_serve_process(pid: int) -> bool:
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    if not cmdline_path.exists():
        return False
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return False
    commandline = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").lower()
    return "pypnm_cmts.cli" in commandline and "serve" in commandline


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def main() -> int:
    args = _parse_args()
    state_path = _resolve_state_path(args.state_path)
    if not state_path.exists():
        print(f"[ERROR] Launch-state file not found: {state_path}", file=sys.stderr)
        return 2

    state = read_launch_state(state_path)
    if state.executable.strip() == "" or not state.argv:
        print(f"[ERROR] Invalid launch-state payload: {state_path}", file=sys.stderr)
        return 2

    command = [state.executable, *state.argv]
    if args.dry_run:
        print(f"[INFO] state={state_path}")
        print(f"[INFO] pid={state.pid}")
        print(f"[INFO] cwd={state.launch_cwd}")
        print(f"[INFO] command={shlex.join(command)}")
        return 0

    if state.pid > 0:
        if not _looks_like_pypnm_serve_process(state.pid):
            print(
                f"[WARN] Recorded pid={state.pid} does not look like pypnm-cmts serve; skipping stop step.",
            )
        else:
            try:
                os.kill(state.pid, signal.SIGTERM)
                print(f"[INFO] Sent SIGTERM to existing serve pid={state.pid}")
            except ProcessLookupError:
                print(f"[INFO] Existing serve pid not running: {state.pid}")
            except PermissionError:
                print(f"[ERROR] Permission denied terminating pid={state.pid}", file=sys.stderr)
                return 1

            deadline = time.time() + 10.0
            while time.time() < deadline:
                if not _is_pid_running(state.pid):
                    break
                time.sleep(0.1)
            else:
                print(f"[WARN] Existing serve pid still running after 10s: {state.pid}")

    env = os.environ.copy()
    env.update(state.env)

    print(f"[INFO] Restarting from launch-state: {state_path}")
    print(f"[INFO] Working directory: {state.launch_cwd}")
    print(f"[INFO] Command: {shlex.join(command)}")
    completed = subprocess.run(
        command,
        cwd=state.launch_cwd,
        env=env,
        check=False,
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

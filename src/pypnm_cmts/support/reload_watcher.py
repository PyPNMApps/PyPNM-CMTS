# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings
from pypnm_cmts.support.web_service_reload import resolve_reload_sentinel_path

RELOAD_WATCHER_PIDFILE_NAME = "pypnm-cmts-reload-watcher.pid"


def resolve_reload_watcher_pidfile_path() -> Path:
    """Return the pidfile path used to track the detached reload watcher."""
    return CmtsSystemConfigSettings.coordination_state_dir() / RELOAD_WATCHER_PIDFILE_NAME


def is_process_running(pid: int) -> bool:
    """Return True when the supplied pid appears to still be alive."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_reload_watcher_pid(pidfile_path: Path | None = None) -> int | None:
    """Read the watcher pidfile if present and return the stored pid."""
    path = pidfile_path or resolve_reload_watcher_pidfile_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if raw == "":
            return None
        return int(raw)
    except (OSError, ValueError):
        return None


def ensure_reload_watcher(
    *,
    project_root: Path,
    python_executable: str | None = None,
) -> tuple[bool, Path]:
    """
    Ensure a detached sentinel watcher is running for the current serve session.

    Returns:
        tuple[bool, Path]: ``(started, pidfile_path)`` where ``started`` is True
        only when a new watcher process was launched.
    """
    pidfile_path = resolve_reload_watcher_pidfile_path()
    existing_pid = read_reload_watcher_pid(pidfile_path)
    if existing_pid is not None and is_process_running(existing_pid):
        return False, pidfile_path

    watcher_script = project_root / "tools" / "support" / "watch_reload_sentinel.py"
    restart_helper = project_root / "tools" / "support" / "restart_from_launch_state.py"
    python_path = python_executable or sys.executable
    restart_cmd = shlex.join([python_path, str(restart_helper)])
    command = [
        python_path,
        str(watcher_script),
        "--sentinel",
        str(resolve_reload_sentinel_path()),
        "--restart-cmd",
        restart_cmd,
        "--pidfile",
        str(pidfile_path),
    ]
    with open(os.devnull, "ab") as devnull:
        subprocess.Popen(
            command,
            cwd=str(project_root),
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
            close_fds=True,
        )
    return True, pidfile_path

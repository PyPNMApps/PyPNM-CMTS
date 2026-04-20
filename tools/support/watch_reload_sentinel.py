#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch a PyPNM-CMTS reload sentinel file and run a restart command.",
    )
    parser.add_argument(
        "--sentinel",
        required=True,
        help="Sentinel file path to watch.",
    )
    parser.add_argument(
        "--restart-cmd",
        required=True,
        help="Shell command to run when the sentinel is created or touched.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=1.0,
        help="Polling interval in seconds. Default: 1.0",
    )
    parser.add_argument(
        "--pidfile",
        default="",
        help="Optional pidfile path to write while the watcher is running.",
    )
    return parser.parse_args()


def _sentinel_mtime(path: Path) -> int:
    if not path.exists():
        return -1
    return int(path.stat().st_mtime_ns)


def _write_pidfile(path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{os.getpid()}\n", encoding="utf-8")


def _remove_pidfile(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return


def main() -> int:
    args = _parse_args()
    sentinel_path = Path(str(args.sentinel)).expanduser()
    restart_cmd = str(args.restart_cmd).strip()
    poll_seconds = max(0.1, float(args.poll_seconds))
    pidfile_value = str(args.pidfile).strip()
    pidfile_path = Path(pidfile_value).expanduser() if pidfile_value != "" else None
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    _write_pidfile(pidfile_path)

    try:
        last_mtime_ns = _sentinel_mtime(sentinel_path)
        print(
            f"[INFO] Watching reload sentinel: {sentinel_path} poll_seconds={poll_seconds}",
            flush=True,
        )
        while True:
            current_mtime_ns = _sentinel_mtime(sentinel_path)
            if current_mtime_ns != -1 and current_mtime_ns != last_mtime_ns:
                print(
                    f"[INFO] Reload sentinel changed: {sentinel_path} restart_cmd={restart_cmd}",
                    flush=True,
                )
                completed = subprocess.run(shlex.split(restart_cmd), check=False)
                if completed.returncode == 0:
                    print(
                        f"[INFO] Restart command completed successfully: {restart_cmd}",
                        flush=True,
                    )
                else:
                    print(
                        f"[WARN] Restart command exited with code={completed.returncode}: {restart_cmd}",
                        flush=True,
                    )
                last_mtime_ns = _sentinel_mtime(sentinel_path)
            elif current_mtime_ns == -1:
                last_mtime_ns = -1
            time.sleep(poll_seconds)
    finally:
        _remove_pidfile(pidfile_path)


if __name__ == "__main__":
    raise SystemExit(main())

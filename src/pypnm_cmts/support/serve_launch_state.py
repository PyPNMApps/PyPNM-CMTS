# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings

LAUNCH_STATE_FILE_NAME = "pypnm-cmts-serve-launch.json"
LAUNCH_STATE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ServeLaunchState:
    schema_version: int
    recorded_at_utc: str
    pid: int
    launch_cwd: str
    executable: str
    argv: list[str]
    env: dict[str, str]


def resolve_launch_state_path() -> Path:
    runtime_dir_callable = getattr(CmtsSystemConfigSettings, "runtime_dir", None)
    if callable(runtime_dir_callable):
        return Path(runtime_dir_callable()) / LAUNCH_STATE_FILE_NAME
    return CmtsSystemConfigSettings.coordination_state_dir() / LAUNCH_STATE_FILE_NAME


def snapshot_restart_env() -> dict[str, str]:
    keep_prefixes = (
        "PYPNM_",
        "PYTHON",
        "VIRTUAL_ENV",
    )
    keep_exact = (
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
    )
    return {
        key: value
        for key, value in os.environ.items()
        if key in keep_exact or key.startswith(keep_prefixes)
    }


def build_launch_state(executable: str, argv: list[str]) -> ServeLaunchState:
    return ServeLaunchState(
        schema_version=LAUNCH_STATE_SCHEMA_VERSION,
        recorded_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        pid=os.getpid(),
        launch_cwd=str(Path.cwd().resolve()),
        executable=str(Path(executable).resolve()),
        argv=[str(value) for value in argv],
        env=snapshot_restart_env(),
    )


def write_launch_state(state: ServeLaunchState) -> Path:
    output_path = resolve_launch_state_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": state.schema_version,
        "recorded_at_utc": state.recorded_at_utc,
        "pid": state.pid,
        "launch_cwd": state.launch_cwd,
        "executable": state.executable,
        "argv": state.argv,
        "env": state.env,
    }

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(output_path.parent),
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(output_path)
    return output_path


def read_launch_state(path: Path | None = None) -> ServeLaunchState:
    source_path = path or resolve_launch_state_path()
    payload = json.loads(source_path.read_text(encoding="utf-8"))

    argv_value = payload.get("argv")
    if not isinstance(argv_value, list):
        raise ValueError("Invalid launch state: argv must be a list.")
    env_value = payload.get("env")
    if not isinstance(env_value, dict):
        raise ValueError("Invalid launch state: env must be an object.")

    return ServeLaunchState(
        schema_version=int(payload.get("schema_version", 0)),
        recorded_at_utc=str(payload.get("recorded_at_utc", "")),
        pid=int(payload.get("pid", 0)),
        launch_cwd=str(payload.get("launch_cwd", "")),
        executable=str(payload.get("executable", "")),
        argv=[str(item) for item in argv_value],
        env={str(key): str(value) for key, value in env_value.items()},
    )

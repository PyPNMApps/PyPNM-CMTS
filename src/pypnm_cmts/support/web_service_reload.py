# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pypnm_cmts.config.runtime_flags import ENV_WEB_SERVICE_RELOAD_SENTINEL
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings

logger = logging.getLogger("WebServiceReload")


def resolve_reload_sentinel_path() -> Path:
    """Return the configured sentinel file used to request a web-service reload."""
    env_value = os.getenv(ENV_WEB_SERVICE_RELOAD_SENTINEL, "").strip()
    if env_value != "":
        return Path(env_value).expanduser()
    return CmtsSystemConfigSettings.web_service_reload_sentinel_path()


def resolve_dev_reload_trigger_path() -> Path:
    """Return the watched Python file used to trigger uvicorn dev reload."""
    return Path(__file__).resolve().parents[1] / "_reload_trigger.py"


def _write_dev_reload_trigger(trigger_path: Path, request_id: str, timestamp: str) -> None:
    """Rewrite the dev reload trigger file with a unique marker payload."""
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        "# SPDX-License-Identifier: Apache-2.0\n"
        "# Copyright (c) 2026 Maurice Garcia\n"
        '"""Auto-generated dev reload trigger module."""\n'
        "\n"
        f'RELOAD_REQUEST_ID = "{request_id}"\n'
        f'RELOAD_REQUESTED_AT = "{timestamp}"\n'
    )
    trigger_path.write_text(payload, encoding="utf-8")


def request_web_service_reload(reason: str, actor: str) -> Path:
    """Persist a reload request to the configured sentinel path."""
    sentinel_path = resolve_reload_sentinel_path()
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    request_id = uuid4().hex
    payload = (
        f"requested_at={timestamp}\n"
        f"request_id={request_id}\n"
        f"actor={actor}\n"
        f"reason={reason}\n"
    )
    logger.info(
        "[WEBSERVICE_RELOAD_REQUEST] actor=%s reason=%s sentinel=%s",
        actor,
        reason,
        sentinel_path,
    )
    # Recreate the sentinel file on each request so both mtime-based and
    # write/create-based external watchers observe the reload request.
    if sentinel_path.exists():
        sentinel_path.unlink()
    sentinel_path.write_text(payload, encoding="utf-8")
    trigger_path = resolve_dev_reload_trigger_path()
    _write_dev_reload_trigger(trigger_path, request_id=request_id, timestamp=timestamp)
    logger.info(
        "[WEBSERVICE_RELOAD_TRIGGER] actor=%s reason=%s trigger=%s",
        actor,
        reason,
        trigger_path,
    )
    return sentinel_path

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
import os
from pathlib import Path

from pypnm_cmts.config.runtime_flags import ENV_WEB_SERVICE_RELOAD_SENTINEL
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings

logger = logging.getLogger("WebServiceReload")


def resolve_reload_sentinel_path() -> Path:
    """Return the configured sentinel file used to request a web-service reload."""
    env_value = os.getenv(ENV_WEB_SERVICE_RELOAD_SENTINEL, "").strip()
    if env_value != "":
        return Path(env_value).expanduser()
    return CmtsSystemConfigSettings.web_service_reload_sentinel_path()


def request_web_service_reload(reason: str, actor: str) -> Path:
    """Persist a reload request to the configured sentinel path."""
    sentinel_path = resolve_reload_sentinel_path()
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(
        "[WEBSERVICE_RELOAD_REQUEST] actor=%s reason=%s sentinel=%s",
        actor,
        reason,
        sentinel_path,
    )
    sentinel_path.touch()
    return sentinel_path

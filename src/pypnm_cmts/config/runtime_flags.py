# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os

ENV_MUTE_PYPNM_ENDPOINTS = "PYPNM_CMTS_MUTE_PYPNM_ENDPOINTS"
ENV_MUTE_TAGS = "PYPNM_CMTS_MUTE_TAGS"
ENV_MUTE_TAGS_HARD = "PYPNM_CMTS_MUTE_TAGS_HARD"
ENV_WEB_SERVICE_RELOAD_SENTINEL = "PYPNM_CMTS_WEB_SERVICE_RELOAD_SENTINEL"
ENV_ENABLE_DEBUG_MEMORY_TOOLS = "PYPNM_CMTS_ENABLE_DEBUG_MEMORY_TOOLS"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_env_flag_enabled(name: str) -> bool:
    """Return True when an environment flag is enabled."""
    value = os.getenv(name, "")
    return value.strip().lower() in _TRUE_VALUES


def read_env_csv_set(name: str) -> set[str]:
    """Read a comma-separated env var as normalized lowercase values."""
    raw = os.getenv(name, "")
    if raw.strip() == "":
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip() != ""}

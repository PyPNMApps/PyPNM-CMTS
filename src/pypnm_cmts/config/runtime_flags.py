# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os

ENV_MUTE_PYPNM_ENDPOINTS = "PYPNM_CMTS_MUTE_PYPNM_ENDPOINTS"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_env_flag_enabled(name: str) -> bool:
    """Return True when an environment flag is enabled."""
    value = os.getenv(name, "")
    return value.strip().lower() in _TRUE_VALUES


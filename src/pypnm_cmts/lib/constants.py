# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from enum import Enum


class OperationalStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


class ReadinessCheck(str, Enum):
    STATE_DIR = "state_dir"
    STATE_DIR_CREATE = "state_dir_create"
    STATE_DIR_ACCESS = "state_dir_access"
    STATE_DIR_READ = "state_dir_read"
    WORKER_SG = "worker_sg"
    SGW_STARTUP = "sgw_startup"
    SGW_DISCOVERY = "sgw_discovery"
    SGW_PRIME = "sgw_prime"
    SGW_CACHE = "sgw_cache"


class CacheRefreshMode(str, Enum):
    NONE = "none"
    LIGHT = "light"
    HEAVY = "heavy"


__all__ = [
    "CacheRefreshMode",
    "OperationalStatus",
    "ReadinessCheck",
]

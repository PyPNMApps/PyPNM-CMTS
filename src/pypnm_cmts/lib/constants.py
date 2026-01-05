# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

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


class RfChannelType(str, Enum):
    SC_QAM = "sc_qam"
    OFDM = "ofdm"
    OFDMA = "ofdma"


__all__ = [
    "CacheRefreshMode",
    "OperationalStatus",
    "RfChannelType",
    "ReadinessCheck",
]

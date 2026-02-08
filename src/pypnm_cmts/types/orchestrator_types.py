from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from enum import Enum


class OrchestratorMode(str, Enum):
    """Execution mode for CMTS orchestration boundaries."""

    STANDALONE = "standalone"
    CONTROLLER = "controller"
    WORKER = "worker"
    COMBINED = "combined"


class AdapterKind(str, Enum):
    """Supported CMTS adapter kinds."""

    SNMP = "snmp"


class ShardMode(str, Enum):
    """Supported service-group sharding strategy."""

    SEQUENTIAL = "sequential"
    SCORE = "score"


__all__ = [
    "AdapterKind",
    "OrchestratorMode",
    "ShardMode",
]

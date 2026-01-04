# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel


def sgw_light_poller(
    _sg_id: ServiceGroupId,
    _settings: CmtsOrchestratorSettings,
    cable_modems: list[SgwCableModemModel],
) -> list[SgwCableModemModel]:
    """
    Placeholder light refresh poller that returns the current modem list.
    """
    return list(cable_modems)


__all__ = [
    "sgw_light_poller",
]

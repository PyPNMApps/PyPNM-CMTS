from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from abc import ABC, abstractmethod

from pypnm_cmts.config.orchestrator_config import (
    CmtsAdapterConfig,
    ServiceGroupDescriptor,
)
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class CmtsAdapter(ABC):
    """
    Abstract CMTS adapter interface.

    Implementations provide CMTS telemetry and inventory boundaries without
    embedding orchestration logic. Phase-1 plugs orchestration flows into
    this interface.
    """

    def __init__(self, config: CmtsAdapterConfig) -> None:
        """Initialize the adapter with CMTS adapter configuration."""
        self._config = config

    @property
    def config(self) -> CmtsAdapterConfig:
        """Return the adapter configuration."""
        return self._config

    @abstractmethod
    def get_sysdescr(self) -> CmtsSysDescrModel:
        """
        Return the CMTS sysDescr payload.

        TODO (Phase-1): Implement SNMP-backed sysDescr collection.
        """

    @abstractmethod
    def list_service_groups(self) -> list[ServiceGroupDescriptor]:
        """
        Return service group descriptors for the CMTS.

        TODO (Phase-1): Implement CMTS service group discovery.
        """

    @abstractmethod
    def refresh(self) -> None:
        """
        Refresh cached adapter data if needed.

        TODO (Phase-1): Implement adapter refresh semantics.
        """

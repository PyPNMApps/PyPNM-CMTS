from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from pypnm_cmts.cmts.adapters.base import CmtsAdapter
from pypnm_cmts.config.orchestrator_config import (
    CmtsAdapterConfig,
    ServiceGroupDescriptor,
)
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class SnmpCmtsAdapter(CmtsAdapter):
    """
    SNMP-backed CMTS adapter stub.

    This adapter is a Phase-0 placeholder. Phase-1 will delegate SNMP
    execution to PyPNM and map results into CMTS descriptors.
    """

    def __init__(self, config: CmtsAdapterConfig) -> None:
        """Initialize the SNMP CMTS adapter."""
        super().__init__(config)

    def get_sysdescr(self) -> CmtsSysDescrModel:
        """
        Return the CMTS sysDescr payload.

        TODO (Phase-1): Delegate to PyPNM SNMP and return parsed sysDescr.
        """
        raise NotImplementedError("Phase-1: implement SNMP sysDescr collection.")

    def list_service_groups(self) -> list[ServiceGroupDescriptor]:
        """
        Return service group descriptors for the CMTS.

        TODO (Phase-1): Delegate to PyPNM SNMP and return service group list.
        """
        raise NotImplementedError("Phase-1: implement SNMP service group discovery.")

    def refresh(self) -> None:
        """
        Refresh cached adapter data if needed.

        TODO (Phase-1): Implement SNMP adapter refresh semantics.
        """
        raise NotImplementedError("Phase-1: implement SNMP adapter refresh.")

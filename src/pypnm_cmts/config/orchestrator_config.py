from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from pydantic import BaseModel, Field, model_validator

from pypnm_cmts.config.config_manager import CmtsConfigManager
from pypnm_cmts.lib.types import OwnerId
from pypnm_cmts.types.orchestrator_types import AdapterKind, OrchestratorMode

DEFAULT_CMTS_INDEX: int = 0
DEFAULT_ORCHESTRATOR_MODE: OrchestratorMode = OrchestratorMode.STANDALONE
DEFAULT_TESTS: list[str] = ["ds_ofdm_rxmer"]
DEFAULT_OWNER_ID: OwnerId = OwnerId("")
DEFAULT_TARGET_SERVICE_GROUPS: int = 0
DEFAULT_WORKER_CAP: int = 0
SHARD_MODE_SEQUENTIAL = "sequential"
SHARD_MODE_SCORE = "score"
SHARD_MODE_OPTIONS = (SHARD_MODE_SEQUENTIAL, SHARD_MODE_SCORE)
DEFAULT_SHARD_MODE = SHARD_MODE_SEQUENTIAL


class CmtsAdapterConfig(BaseModel):
    """Configuration for CMTS adapter selection and targeting."""

    kind: AdapterKind = Field(default=AdapterKind.SNMP, description="CMTS adapter kind.")
    cmts_index: int = Field(default=DEFAULT_CMTS_INDEX, description="Index of the CMTS entry in system.json.")
    label: str = Field(default="primary", description="Human-friendly adapter label.")


class ServiceGroupDescriptor(BaseModel):
    """Descriptor for a CMTS service group boundary."""

    sg_id: str = Field(default="", description="Service group identifier.")
    name: str = Field(default="", description="Service group name or label.")
    cmts_index: int = Field(default=DEFAULT_CMTS_INDEX, description="CMTS index for the service group.")
    enabled: bool = Field(default=True, description="Whether the service group is enabled for orchestration.")


class CmtsOrchestratorSettings(BaseModel):
    """Top-level orchestrator settings for CMTS control boundaries."""

    mode: OrchestratorMode = Field(default=DEFAULT_ORCHESTRATOR_MODE, description="Orchestrator execution mode.")
    adapter: CmtsAdapterConfig = Field(default_factory=CmtsAdapterConfig, description="CMTS adapter configuration.")
    service_groups: list[ServiceGroupDescriptor] = Field(default_factory=list, description="Service group descriptors.")
    default_tests: list[str] = Field(default_factory=list, description="Default test names for orchestration.")
    owner_id: OwnerId = Field(default=DEFAULT_OWNER_ID, description="Optional explicit owner id for coordination.")
    target_service_groups: int = Field(default=DEFAULT_TARGET_SERVICE_GROUPS, description="Target number of service groups per replica.")
    shard_mode: str = Field(default=DEFAULT_SHARD_MODE, description="Service group shard mode: sequential or score.")
    worker_cap: int = Field(default=DEFAULT_WORKER_CAP, description="Optional cap on worker count (0 means no cap).")

    @model_validator(mode="after")
    def _apply_default_tests(self) -> CmtsOrchestratorSettings:
        if not self.default_tests:
            self.default_tests = list(DEFAULT_TESTS)
        if self.shard_mode not in SHARD_MODE_OPTIONS:
            raise ValueError("shard_mode must be 'sequential' or 'score'.")
        if int(self.target_service_groups) < 0:
            raise ValueError("target_service_groups must be non-negative.")
        if int(self.worker_cap) < 0:
            raise ValueError("worker_cap must be non-negative.")
        return self

    @classmethod
    def from_system_config(cls, config_path: str | None = None) -> CmtsOrchestratorSettings:
        """
        Build orchestrator configuration from system.json.

        TODO (Phase-1): Expand validation once orchestration fields stabilize.
        """
        manager = CmtsConfigManager(config_path=config_path)
        data = manager.get("CmtsOrchestrator")
        if data is None:
            return cls()
        if isinstance(data, dict):
            return cls.model_validate(data)
        return cls()

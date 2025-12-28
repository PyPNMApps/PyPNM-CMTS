from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pypnm.lib.types import HostNameStr, SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.config.config_manager import CmtsConfigManager
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.types.orchestrator_types import AdapterKind, OrchestratorMode

DEFAULT_CMTS_INDEX: int = 0
DEFAULT_ORCHESTRATOR_MODE: OrchestratorMode = OrchestratorMode.STANDALONE
DEFAULT_TESTS: list[str] = ["ds_ofdm_rxmer"]
DEFAULT_OWNER_ID: OwnerId = OwnerId("")
DEFAULT_TARGET_SERVICE_GROUPS: int = 0
DEFAULT_WORKER_CAP: int = 0
DEFAULT_STATE_DIR = Path(".data/coordination")
DEFAULT_ELECTION_NAME: CoordinationElectionName = CoordinationElectionName("")
DEFAULT_LEADER_TTL_SECONDS = 10
DEFAULT_LEASE_TTL_SECONDS = 10
DEFAULT_TICK_INTERVAL_SECONDS = 1.0
DEFAULT_SNMP_COMMUNITY: SnmpReadCommunity = SnmpReadCommunity("public")
DEFAULT_SNMP_PORT = 161
SHARD_MODE_SEQUENTIAL = "sequential"
SHARD_MODE_SCORE = "score"
SHARD_MODE_OPTIONS = (SHARD_MODE_SEQUENTIAL, SHARD_MODE_SCORE)
DEFAULT_SHARD_MODE = SHARD_MODE_SEQUENTIAL


class CmtsAdapterConfig(BaseModel):
    """Configuration for CMTS adapter selection and targeting."""

    kind: AdapterKind = Field(default=AdapterKind.SNMP, description="CMTS adapter kind.")
    cmts_index: int = Field(default=DEFAULT_CMTS_INDEX, description="Index of the CMTS entry in system.json.")
    label: str = Field(default="primary", description="Human-friendly adapter label.")
    hostname: HostNameStr = Field(default=HostNameStr(""), description="CMTS hostname or IP address.")
    community: SnmpReadCommunity = Field(default=DEFAULT_SNMP_COMMUNITY, description="SNMPv2c read community string.")
    write_community: SnmpWriteCommunity = Field(default=SnmpWriteCommunity(""), description="Optional SNMPv2c write community string.")
    port: int = Field(default=DEFAULT_SNMP_PORT, description="SNMP port for CMTS discovery.")


class ServiceGroupDescriptor(BaseModel):
    """Descriptor for a CMTS service group boundary."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    name: str = Field(default="", description="Service group name or label.")
    cmts_index: int = Field(default=DEFAULT_CMTS_INDEX, description="CMTS index for the service group.")
    enabled: bool = Field(default=True, description="Whether the service group is enabled for orchestration.")

    @model_validator(mode="after")
    def _validate_sg_id(self) -> ServiceGroupDescriptor:
        if int(self.sg_id) <= 0:
            raise ValueError("sg_id must be greater than zero.")
        return self


class CmtsOrchestratorSettings(BaseModel):
    """Top-level orchestrator settings for CMTS control boundaries."""

    mode: OrchestratorMode = Field(default=DEFAULT_ORCHESTRATOR_MODE, description="Orchestrator execution mode.")
    adapter: CmtsAdapterConfig = Field(default_factory=CmtsAdapterConfig, description="CMTS adapter configuration.")
    service_groups: list[ServiceGroupDescriptor] = Field(default_factory=list, description="Service group descriptors.")
    auto_discover: bool = Field(default=False, description="Enable CMTS-based service group discovery.")
    default_tests: list[str] = Field(default_factory=list, description="Default test names for orchestration.")
    owner_id: OwnerId = Field(default=DEFAULT_OWNER_ID, description="Optional explicit owner id for coordination.")
    target_service_groups: int = Field(default=DEFAULT_TARGET_SERVICE_GROUPS, description="Target number of service groups per replica.")
    shard_mode: str = Field(default=DEFAULT_SHARD_MODE, description="Service group shard mode: sequential or score.")
    worker_cap: int = Field(default=DEFAULT_WORKER_CAP, description="Optional cap on worker count (0 means no cap).")
    tick_interval_seconds: float = Field(default=DEFAULT_TICK_INTERVAL_SECONDS, description="Tick interval in seconds.")
    leader_ttl_seconds: int = Field(default=DEFAULT_LEADER_TTL_SECONDS, description="Leader election TTL in seconds.")
    lease_ttl_seconds: int = Field(default=DEFAULT_LEASE_TTL_SECONDS, description="Service group lease TTL in seconds.")
    state_dir: CoordinationPath = Field(default=DEFAULT_STATE_DIR, description="State directory for coordination files.")
    election_name: CoordinationElectionName = Field(default=DEFAULT_ELECTION_NAME, description="Optional election name override.")

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
        if float(self.tick_interval_seconds) <= 0:
            raise ValueError("tick_interval_seconds must be greater than zero.")
        if int(self.leader_ttl_seconds) <= 0:
            raise ValueError("leader_ttl_seconds must be greater than zero.")
        if int(self.lease_ttl_seconds) <= 0:
            raise ValueError("lease_ttl_seconds must be greater than zero.")
        min_ttl = min(int(self.leader_ttl_seconds), int(self.lease_ttl_seconds))
        if float(self.tick_interval_seconds) >= float(min_ttl):
            raise ValueError("tick_interval_seconds must be less than leader_ttl_seconds and lease_ttl_seconds.")
        if bool(self.auto_discover):
            hostname_value = str(self.adapter.hostname).strip()
            if hostname_value == "":
                raise ValueError("adapter.hostname must be set when auto_discover is enabled.")
            community_value = str(self.adapter.community).strip()
            if community_value == "":
                raise ValueError("adapter.community must be set when auto_discover is enabled.")
        if isinstance(self.state_dir, str):
            if self.state_dir.strip() == "":
                raise ValueError("state_dir must be non-empty.")
            self.state_dir = Path(self.state_dir)
        if str(self.election_name).strip() == "":
            self.election_name = DEFAULT_ELECTION_NAME
        return self

    @classmethod
    def from_system_config(cls, config_path: CoordinationPath | None = None) -> CmtsOrchestratorSettings:
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

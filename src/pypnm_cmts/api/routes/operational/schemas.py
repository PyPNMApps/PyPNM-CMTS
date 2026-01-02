# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    ServiceGroupId,
)
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class OperationalIdentityModel(BaseModel):
    """Runtime identity metadata for operational endpoints."""

    mode: OrchestratorMode = Field(default=OrchestratorMode.STANDALONE, description="Current orchestrator mode.")
    election_name: CoordinationElectionName | None = Field(default=None, description="Election name for coordination.")
    state_dir: CoordinationPath | None = Field(default=None, description="Coordination state directory.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Bound service group id for worker mode.")


class HealthResponseModel(BaseModel):
    """Health endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Health status indicator.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")


class ReadyResponseModel(BaseModel):
    """Readiness endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Readiness status indicator.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    failed_check: ReadinessCheck | None = Field(default=None, description="Name of the first failing readiness check.")
    message: str = Field(default="", description="Human-readable readiness message.")
    discovery_ok: bool = Field(default=False, description="Whether SG discovery completed successfully.")
    discovered_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Discovered service group identifiers.")
    sgw_ready: bool = Field(default=False, description="Whether SGW cache is primed for all discovered SGs.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups missing cache priming.")


class OperationalProcessInfoModel(BaseModel):
    """Operational process snapshot for controller and worker processes."""

    pidfile_path: CoordinationPath | None = Field(default=None, description="PID file path for the process.")
    pidfile_exists: bool = Field(default=False, description="Whether the PID file exists.")
    pid: int | None = Field(default=None, description="PID value if available.")
    is_running: bool = Field(default=False, description="Whether the PID is currently running.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Service group id derived from pidfile naming.")


class OperationalStatusResponseModel(BaseModel):
    """Operational status endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Operational status indicator.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    controller: OperationalProcessInfoModel = Field(default_factory=OperationalProcessInfoModel, description="Controller process snapshot.")
    workers: list[OperationalProcessInfoModel] = Field(default_factory=list, description="Worker process snapshots.")
    pid_records_missing: bool = Field(default=False, description="True when pidfiles are missing from state_dir.")
    pid_records_stale: bool = Field(default=False, description="True when pidfiles exist but none are running.")
    fallback_used: bool = Field(default=False, description="True when fallback discovery returns matching processes.")


class VersionResponseModel(BaseModel):
    """Version endpoint response."""

    application: str = Field(default="pypnm-cmts", description="Application name.")
    version: str = Field(default="", description="Package version string.")
    python_version: str = Field(default="", description="Python interpreter version.")
    build_metadata: str = Field(default="", description="Optional build metadata string.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")


__all__ = [
    "OperationalIdentityModel",
    "HealthResponseModel",
    "ReadyResponseModel",
    "OperationalProcessInfoModel",
    "OperationalStatusResponseModel",
    "VersionResponseModel",
]

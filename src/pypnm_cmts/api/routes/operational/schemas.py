# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.types import TimeStamp

from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    ServiceGroupId,
)
from pypnm_cmts.sgw.models import (
    SgwWorkerPollIntervalDebugModel,
    SgwWorkerProcessDebugModel,
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
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")


class ReadyResponseModel(BaseModel):
    """Readiness endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Readiness status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
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
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
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
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")


class SgwProcessResponseModel(BaseModel):
    """SGW worker process debug response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="SGW debug status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    workers: list[SgwWorkerProcessDebugModel] = Field(default_factory=list, description="SGW worker process snapshots.")
    message: str = Field(default="", description="Optional error message when unavailable.")


class SgwPollIntervalResponseModel(BaseModel):
    """SGW poll interval debug response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="SGW debug status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    workers: list[SgwWorkerPollIntervalDebugModel] = Field(default_factory=list, description="SGW poll interval snapshots.")
    message: str = Field(default="", description="Optional error message when unavailable.")


class MemorySgwCacheDebugModel(BaseModel):
    """Lightweight SGW cache memory-debug counters."""

    service_group_count: int = Field(default=0, ge=0, description="Number of SG cache entries.")
    modem_count: int = Field(default=0, ge=0, description="Number of cached cable modem rows across all SGs.")
    sysdescr_count: int = Field(default=0, ge=0, description="Number of cached modem sysDescr payloads with non-empty text.")
    sysdescr_text_bytes: int = Field(default=0, ge=0, description="Approximate UTF-8 bytes across cached sysDescr text.")
    ds_rf_channel_count: int = Field(default=0, ge=0, description="Number of cached downstream RF channel rows.")
    us_rf_channel_count: int = Field(default=0, ge=0, description="Number of cached upstream RF channel rows.")
    mac_text_bytes: int = Field(default=0, ge=0, description="Approximate bytes used by cached MAC address text.")
    ipv4_text_bytes: int = Field(default=0, ge=0, description="Approximate bytes used by cached IPv4 text.")
    ipv6_text_bytes: int = Field(default=0, ge=0, description="Approximate bytes used by cached IPv6 text.")
    entry_dict_shallow_bytes: int = Field(default=0, ge=0, description="Shallow size of the SGW cache entry dictionary.")


class MemoryOperationDebugModel(BaseModel):
    """Filesystem-backed operation-store debug counters."""

    operation_dir_count: int = Field(default=0, ge=0, description="Number of operation directories on disk.")
    result_file_count: int = Field(default=0, ge=0, description="Number of operation result files on disk.")
    state_file_count: int = Field(default=0, ge=0, description="Number of operation state files on disk.")
    cancel_flag_count: int = Field(default=0, ge=0, description="Number of operation cancel-flag files on disk.")
    total_bytes: int = Field(default=0, ge=0, description="Approximate total bytes under the operation store base directory.")
    base_dir: str = Field(default="", description="Resolved operation store base directory.")


class MemoryPnmRunnerDebugModel(BaseModel):
    """Live PNM operation-service and runner counters."""

    service_name: str = Field(default="", description="PNM operation service class name.")
    thread_count: int = Field(default=0, ge=0, description="Tracked background runner thread count for the service.")
    alive_thread_count: int = Field(default=0, ge=0, description="Alive background runner thread count for the service.")
    tracked_operation_count: int = Field(default=0, ge=0, description="Active operation debug snapshot count for the service.")
    total_pending_futures: int = Field(default=0, ge=0, description="Aggregate pending futures across active operations.")
    total_abandoned_futures: int = Field(default=0, ge=0, description="Aggregate timed-out futures still tracked as abandoned.")
    total_retry_queue_items: int = Field(default=0, ge=0, description="Aggregate queued retries across active operations.")
    total_queue_items: int = Field(default=0, ge=0, description="Aggregate queued work items across active operations.")


class MemoryThreadDebugModel(BaseModel):
    """Live Python thread inventory snapshot."""

    name: str = Field(default="", description="Python thread name.")
    ident: int | None = Field(default=None, description="Python thread identifier when available.")
    native_id: int | None = Field(default=None, description="Native thread identifier when available.")
    daemon: bool = Field(default=False, description="Whether the thread is daemonized.")
    alive: bool = Field(default=False, description="Whether the thread is alive.")


class MemoryObjectTypeDebugModel(BaseModel):
    """Bounded Python object-family summary."""

    type_name: str = Field(default="", description="Qualified type name for the object family.")
    count: int = Field(default=0, ge=0, description="Number of live GC-tracked objects for the type.")
    shallow_bytes: int = Field(default=0, ge=0, description="Approximate shallow bytes across sampled objects for the type.")


class MemoryDetailResponseModel(BaseModel):
    """Operational memory-debug response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Memory-debug status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    process_rss_bytes: int = Field(default=0, ge=0, description="Current process RSS in bytes.")
    sgw_cache: MemorySgwCacheDebugModel = Field(default_factory=MemorySgwCacheDebugModel, description="SGW cache counters and byte estimates.")
    operations: MemoryOperationDebugModel = Field(default_factory=MemoryOperationDebugModel, description="Operation-store disk counters.")
    pnm_runners: list[MemoryPnmRunnerDebugModel] = Field(default_factory=list, description="Live in-memory PNM operation-service runner counters.")
    threads: list[MemoryThreadDebugModel] = Field(default_factory=list, description="Live Python thread inventory.")
    python_gc: list[MemoryObjectTypeDebugModel] = Field(default_factory=list, description="Top GC-tracked Python object families by count and shallow size.")
    message: str = Field(default="", description="Optional informational message.")


class MemoryReleaseResponseModel(BaseModel):
    """Operational memory-release response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Memory-release status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    rss_before_bytes: int = Field(default=0, ge=0, description="Process RSS in bytes before the release attempt.")
    rss_after_bytes: int = Field(default=0, ge=0, description="Process RSS in bytes after the release attempt.")
    reclaimed_bytes: int = Field(default=0, ge=0, description="Observed RSS reduction in bytes after the release attempt.")
    message: str = Field(default="", description="Informational result message.")


class MemoryAllocateRequestModel(BaseModel):
    """Operational debug memory-allocation request."""

    megabytes: int = Field(default=0, ge=1, le=4096, description="MiB to allocate and retain in-process for debug testing.")


class MemoryAllocateResponseModel(BaseModel):
    """Operational debug memory-allocation response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Memory-allocation status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    requested_megabytes: int = Field(default=0, ge=0, description="Requested retained allocation size in MiB.")
    rss_before_bytes: int = Field(default=0, ge=0, description="Process RSS in bytes before the retained allocation.")
    rss_after_bytes: int = Field(default=0, ge=0, description="Process RSS in bytes after the retained allocation.")
    retained_bytes: int = Field(default=0, ge=0, description="Total retained debug-allocation bytes after the request.")
    message: str = Field(default="", description="Informational result message.")


class SgwRestartRequestModel(BaseModel):
    """SGW restart request payload."""

    worker_id: str = Field(default="", description="Serving group worker identifier (sgw-<id> or numeric).")


class SgwRestartResponseModel(BaseModel):
    """SGW restart response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="SGW restart status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Parsed service group identifier when available.")
    message: str = Field(default="", description="Restart status message.")


class SgwResetRequestModel(BaseModel):
    """SGW refresh counter reset request payload."""

    worker_id: str = Field(default="", description="Serving group worker identifier (sgw-<id> or numeric).")


class SgwResetResponseModel(BaseModel):
    """SGW refresh counter reset response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="SGW reset status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Parsed service group identifier when available.")
    message: str = Field(default="", description="Reset status message.")


__all__ = [
    "OperationalIdentityModel",
    "HealthResponseModel",
    "ReadyResponseModel",
    "OperationalProcessInfoModel",
    "OperationalStatusResponseModel",
    "VersionResponseModel",
    "SgwProcessResponseModel",
    "SgwPollIntervalResponseModel",
    "MemorySgwCacheDebugModel",
    "MemoryOperationDebugModel",
    "MemoryPnmRunnerDebugModel",
    "MemoryThreadDebugModel",
    "MemoryObjectTypeDebugModel",
    "MemoryDetailResponseModel",
    "MemoryReleaseResponseModel",
    "MemoryAllocateRequestModel",
    "MemoryAllocateResponseModel",
    "SgwRestartRequestModel",
    "SgwRestartResponseModel",
    "SgwResetRequestModel",
    "SgwResetResponseModel",
]

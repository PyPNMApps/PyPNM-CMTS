# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import logging
import pathlib
import re
from time import monotonic, time

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pypnm.lib.types import String, TimestampSec

from pypnm_cmts.lib.types import (
    ByteCount,
    HealthDataPathStr,
    HealthDirectorySizes,
    HealthMessageStr,
    HealthServiceName,
    HealthStartTime,
    HealthStatus,
    HealthUptimeSeconds,
    HealthVersionStr,
    PercentValue,
)

CMTS_HEALTH_START_MONOTONIC: float = monotonic()
CMTS_HEALTH_START_EPOCH: HealthStartTime = TimestampSec(int(time()))


def _read_project_name() -> HealthServiceName:
    """Read the CMTS package name from pyproject.toml with a stable fallback."""
    pyproject_path = pathlib.Path(__file__).resolve()
    while pyproject_path.name != "src" and pyproject_path != pyproject_path.parent:
        pyproject_path = pyproject_path.parent
    pyproject_path = pyproject_path.parent / "pyproject.toml"
    if not pyproject_path.is_file():
        return "pypnm-docsis-cmts"

    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    project_match = re.search(r"^\[project\]\s*$", pyproject_text, re.MULTILINE)
    if project_match is None:
        return "pypnm-docsis-cmts"

    tail_text = pyproject_text[project_match.end() :]
    name_match = re.search(r'^\s*name\s*=\s*"([^"]+)"\s*$', tail_text, re.MULTILINE)
    if name_match is None:
        return "pypnm-docsis-cmts"

    project_name = name_match.group(1).strip()
    if project_name != "pypnm-docsis-cmts":
        return "pypnm-docsis-cmts"
    return "pypnm-docsis-cmts"


CMTS_SERVICE_NAME: HealthServiceName = _read_project_name()


class HealthServiceInfo(BaseModel):
    """Service identity metadata for the CMTS health response."""

    model_config = ConfigDict(extra="allow")

    name: HealthServiceName
    version: HealthVersionStr | None = None


class HealthUptimeInfo(BaseModel):
    """CMTS process uptime metrics."""

    model_config = ConfigDict(extra="allow")

    starttime: HealthStartTime | None = Field(default=None, ge=0)
    uptime: HealthUptimeSeconds | None = Field(default=None, ge=0)


class HealthMemoryInfo(BaseModel):
    """CMTS process and host memory metrics."""

    model_config = ConfigDict(extra="allow")

    rss_bytes: ByteCount | None = Field(default=None, ge=0)
    total_bytes: ByteCount | None = Field(default=None, ge=0)
    free_bytes: ByteCount | None = Field(default=None, ge=0)
    available_bytes: ByteCount | None = Field(default=None, ge=0)
    usage_percent: PercentValue | None = Field(default=None, ge=0, le=100)


class HealthDataInfo(BaseModel):
    """CMTS runtime data directory metrics."""

    model_config = ConfigDict(extra="allow")

    path: HealthDataPathStr | None = None
    size_bytes: ByteCount | None = Field(default=None, ge=0)
    directories: HealthDirectorySizes | None = None

    @field_validator("directories")
    @classmethod
    def validate_directories(cls, value: HealthDirectorySizes | None) -> HealthDirectorySizes | None:
        """Ensure reported per-directory sizes are non-negative."""
        if value is None:
            return value
        for key, size in value.items():
            if size < 0:
                raise ValueError(f"directories[{key}] must be >= 0")
        return value


class HealthResponseModel(BaseModel):
    """CMTS health response contract for the top-level `/health` endpoint."""

    model_config = ConfigDict(extra="allow")

    status: HealthStatus
    message: HealthMessageStr | None = None
    service: HealthServiceInfo
    uptime: HealthUptimeInfo | None = None
    memory: HealthMemoryInfo | None = None
    data: HealthDataInfo | None = None


class CmtsHealthService:
    """Collect and assemble resilient CMTS health telemetry."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_response(self, version: String) -> HealthResponseModel:
        """Build the CMTS health response, tolerating partial telemetry failures."""
        uptime = self._collect_uptime_info()
        memory = self._collect_memory_info()
        data = self._collect_data_info()

        missing_sections: list[str] = []
        missing_metrics: list[str] = []

        if uptime is None:
            missing_sections.append("uptime")
        else:
            missing_metrics.extend(self._missing_uptime_metrics(uptime))

        if memory is None:
            missing_sections.append("memory")
        else:
            missing_metrics.extend(self._missing_memory_metrics(memory))

        if data is None:
            missing_sections.append("data")
        else:
            missing_metrics.extend(self._missing_data_metrics(data))

        status: HealthStatus = "ok"
        message: HealthMessageStr | None = None
        if missing_sections or missing_metrics:
            status = "warning"
            detail_parts: list[str] = []
            if missing_sections:
                detail_parts.append(f"missing sections: {', '.join(missing_sections)}")
            if missing_metrics:
                detail_parts.append(f"missing metrics: {', '.join(missing_metrics)}")
            message = HealthMessageStr("; ".join(detail_parts))

        response = HealthResponseModel(
            status=status,
            message=message,
            service=HealthServiceInfo(
                name=CMTS_SERVICE_NAME,
                version=HealthVersionStr(version),
            ),
            uptime=uptime,
            memory=memory,
            data=data,
        )
        return response.model_copy(update={"version": version})

    def _collect_uptime_info(self) -> HealthUptimeInfo | None:
        """Collect process uptime metrics."""
        with self._guard_metric("uptime"):
            elapsed_seconds = max(monotonic() - CMTS_HEALTH_START_MONOTONIC, 0.0)
            return HealthUptimeInfo(
                starttime=CMTS_HEALTH_START_EPOCH,
                uptime=HealthUptimeSeconds(int(elapsed_seconds)),
            )
        return None

    def _collect_memory_info(self) -> HealthMemoryInfo | None:
        """Collect memory metrics for the running process and host."""
        rss_bytes = self._read_proc_status_bytes("VmRSS")
        total_bytes = self._read_meminfo_bytes("MemTotal")
        free_bytes = self._read_meminfo_bytes("MemFree")
        available_bytes = self._read_meminfo_bytes("MemAvailable")
        usage_percent = self._compute_usage_percent(rss_bytes, total_bytes)
        return HealthMemoryInfo(
            rss_bytes=rss_bytes,
            total_bytes=total_bytes,
            free_bytes=free_bytes,
            available_bytes=available_bytes,
            usage_percent=usage_percent,
        )

    def _collect_data_info(self) -> HealthDataInfo | None:
        """Collect runtime data directory metrics."""
        data_root = pathlib.Path(".data")
        size_bytes = self._folder_size_bytes(data_root)
        directories = self._first_level_directory_sizes(data_root)
        return HealthDataInfo(
            path=HealthDataPathStr(str(data_root)),
            size_bytes=size_bytes,
            directories=directories,
        )

    def _read_proc_status_bytes(self, field_name: String) -> ByteCount | None:
        """Read a memory field from `/proc/self/status` in bytes."""
        status_path = pathlib.Path("/proc/self/status")
        if not status_path.is_file():
            return None
        with self._guard_metric(field_name):
            for line in status_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith(f"{field_name}:"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    return None
                return ByteCount(int(parts[1]) * 1024)
        return None

    def _read_meminfo_bytes(self, field_name: String) -> ByteCount | None:
        """Read a `/proc/meminfo` field in bytes."""
        meminfo_path = pathlib.Path("/proc/meminfo")
        if not meminfo_path.is_file():
            return None
        with self._guard_metric(field_name):
            for line in meminfo_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith(f"{field_name}:"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    return None
                return ByteCount(int(parts[1]) * 1024)
        return None

    def _compute_usage_percent(
        self,
        rss_bytes: ByteCount | None,
        total_bytes: ByteCount | None,
    ) -> PercentValue | None:
        """Compute process RSS as a percentage of total host memory."""
        if rss_bytes is None or total_bytes is None or total_bytes <= 0:
            return None
        usage_percent = round((rss_bytes / total_bytes) * 100.0, 2)
        if usage_percent < 0:
            return PercentValue(0.0)
        if usage_percent > 100:
            return PercentValue(100.0)
        return PercentValue(usage_percent)

    def _folder_size_bytes(self, folder_path: pathlib.Path) -> ByteCount | None:
        """Return recursive size for a folder, or `None` when unavailable."""
        if not folder_path.exists():
            return None
        total_bytes = 0
        with self._guard_metric(f"folder-size:{folder_path}"):
            for path in folder_path.rglob("*"):
                file_size = self._file_size_bytes(path)
                if file_size is None:
                    continue
                total_bytes += file_size
        return ByteCount(total_bytes)

    def _file_size_bytes(self, path: pathlib.Path) -> ByteCount | None:
        """Return file size in bytes, or `None` for non-files and inaccessible paths."""
        with self._guard_metric(f"file-size:{path}"):
            if path.is_file():
                return ByteCount(path.stat().st_size)
        return None

    def _first_level_directory_sizes(self, folder_path: pathlib.Path) -> HealthDirectorySizes | None:
        """Return recursive sizes for first-level directories, or `None` when unavailable."""
        if not folder_path.exists():
            return None
        sizes: HealthDirectorySizes = {}
        with self._guard_metric(f"dir-sizes:{folder_path}"):
            for child in folder_path.iterdir():
                with self._guard_metric(f"dir-entry:{child}"):
                    if not child.is_dir():
                        continue
                child_size = self._folder_size_bytes(child)
                if child_size is None:
                    continue
                sizes[child.name] = child_size
        return sizes

    def _missing_uptime_metrics(self, uptime: HealthUptimeInfo) -> list[str]:
        """Return names of missing uptime metrics."""
        missing_metrics: list[str] = []
        if uptime.starttime is None:
            missing_metrics.append("uptime.starttime")
        if uptime.uptime is None:
            missing_metrics.append("uptime.uptime")
        return missing_metrics

    def _missing_memory_metrics(self, memory: HealthMemoryInfo) -> list[str]:
        """Return names of missing memory metrics."""
        missing_metrics: list[str] = []
        if memory.rss_bytes is None:
            missing_metrics.append("memory.rss_bytes")
        if memory.total_bytes is None:
            missing_metrics.append("memory.total_bytes")
        if memory.free_bytes is None:
            missing_metrics.append("memory.free_bytes")
        if memory.available_bytes is None:
            missing_metrics.append("memory.available_bytes")
        if memory.usage_percent is None:
            missing_metrics.append("memory.usage_percent")
        return missing_metrics

    def _missing_data_metrics(self, data: HealthDataInfo) -> list[str]:
        """Return names of missing data metrics."""
        missing_metrics: list[str] = []
        if data.path is None:
            missing_metrics.append("data.path")
        if data.size_bytes is None:
            missing_metrics.append("data.size_bytes")
        if data.directories is None:
            missing_metrics.append("data.directories")
        return missing_metrics

    def _guard_metric(self, metric_name: str) -> _MetricGuard:
        """Wrap telemetry collection to prevent individual failures from surfacing."""
        return _MetricGuard(self.logger, metric_name)


class _MetricGuard:
    """Internal-only metric guard that suppresses telemetry collection failures."""

    def __init__(self, logger: logging.Logger, metric_name: str) -> None:
        self._logger = logger
        self._metric_name = metric_name

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _traceback: object,
    ) -> bool:
        if exc is None:
            return False
        self._logger.warning("[HEALTH_METRIC_UNAVAILABLE] metric=%s error=%s", self._metric_name, exc)
        return True


__all__ = [
    "CMTS_SERVICE_NAME",
    "CmtsHealthService",
    "HealthDataInfo",
    "HealthMemoryInfo",
    "HealthResponseModel",
    "HealthServiceInfo",
    "HealthStatus",
    "HealthUptimeInfo",
]

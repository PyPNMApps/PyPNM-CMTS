# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.types import TimeStamp

from pypnm_cmts.api.routes.operational.schemas import OperationalIdentityModel
from pypnm_cmts.lib.constants import OperationalStatus


class DebugMemoryAllocateRequestModel(BaseModel):
    """Debug retained-memory allocation request."""

    megabytes: int = Field(default=0, ge=1, le=4096, description="MiB to allocate and retain in-process for debug testing.")


class DebugMemoryAllocateResponseModel(BaseModel):
    """Debug retained-memory allocation response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Debug memory-allocation status indicator.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    requested_megabytes: int = Field(default=0, ge=0, description="Requested retained allocation size in MiB.")
    rss_before_bytes: int = Field(default=0, ge=0, description="Process RSS in bytes before the retained allocation.")
    rss_after_bytes: int = Field(default=0, ge=0, description="Process RSS in bytes after the retained allocation.")
    retained_bytes: int = Field(default=0, ge=0, description="Total retained debug-allocation bytes after the request.")
    message: str = Field(default="", description="Informational result message.")


__all__ = [
    "DebugMemoryAllocateRequestModel",
    "DebugMemoryAllocateResponseModel",
]

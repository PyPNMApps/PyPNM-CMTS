# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.lib.types import TimeStamp
from pypnm.lib.utils import Generate, TimeUnit

from pypnm_cmts.api.routes.debug.schemas import (
    DebugMemoryAllocateRequestModel,
    DebugMemoryAllocateResponseModel,
)
from pypnm_cmts.api.routes.operational.service import OperationalService
from pypnm_cmts.lib.constants import OperationalStatus
from pypnm_cmts.support.debug_memory_tools import allocate_retained_debug_memory_mb
from pypnm_cmts.support.worker_guard import read_process_rss_bytes


class DebugService:
    """Service layer for debug-only endpoints."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._operational_service = OperationalService()

    def allocate_memory(self, payload: DebugMemoryAllocateRequestModel) -> DebugMemoryAllocateResponseModel:
        """Retain process memory so the web-service RSS guard can be exercised on demand."""
        meta = self._operational_service.build_identity()
        rss_before_bytes = read_process_rss_bytes()
        retained_bytes = allocate_retained_debug_memory_mb(int(payload.megabytes))
        rss_after_bytes = read_process_rss_bytes()
        self.logger.warning(
            "[DEBUG_MEMORY_ALLOCATE] requested_mb=%s rss_before_bytes=%s rss_after_bytes=%s retained_bytes=%s",
            payload.megabytes,
            rss_before_bytes,
            rss_after_bytes,
            retained_bytes,
        )
        return DebugMemoryAllocateResponseModel(
            status=OperationalStatus.OK,
            timestamp=TimeStamp(Generate.time_stamp(unit=TimeUnit.SECONDS)),
            meta=meta,
            requested_megabytes=int(payload.megabytes),
            rss_before_bytes=rss_before_bytes,
            rss_after_bytes=rss_after_bytes,
            retained_bytes=retained_bytes,
            message="Retained debug memory allocation in-process; wait for the RSS guard poll interval.",
        )


__all__ = ["DebugService"]

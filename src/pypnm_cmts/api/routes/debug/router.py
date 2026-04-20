# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.debug.schemas import (
    DebugMemoryAllocateRequestModel,
    DebugMemoryAllocateResponseModel,
)
from pypnm_cmts.api.routes.debug.service import DebugService
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class DebugRouter:
    """FastAPI router for debug-only endpoints."""

    def __init__(
        self,
        prefix: str = "/ops/debug",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["Debug"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._service = DebugService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/allocateMemory",
            response_model=DebugMemoryAllocateResponseModel,
            summary="Debug retained-memory allocation",
            description="Development-only tool that retains process memory so the web-service RSS guard can be exercised.",
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        def allocate_memory(payload: DebugMemoryAllocateRequestModel) -> DebugMemoryAllocateResponseModel:
            """
            **Debug Allocate Memory**

            Retains memory inside the running process for RSS-guard testing.
            """
            return self._service.allocate_memory(payload)


router = DebugRouter().router

__all__ = ["router"]

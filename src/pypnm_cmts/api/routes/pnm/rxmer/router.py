# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter, Request

from pypnm_cmts.api.routes.pnm.rxmer.schemas import (
    RxMerServiceGroupCaptureRequest,
    RxMerServiceGroupCaptureResponse,
)
from pypnm_cmts.api.routes.pnm.rxmer.service import RxMerServiceGroupCaptureService
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class RxMerRouter:
    """
    FastAPI router for RxMER orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/rxmer",
        tags: list[str | Enum] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM RxMER"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = RxMerServiceGroupCaptureService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/getCapture",
            response_model=RxMerServiceGroupCaptureResponse,
            summary="Orchestrate RxMER capture for a serving group",
            description="Triggers concurrent RxMER capture per cable modem using the SGW cache.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        async def get_capture(
            payload: RxMerServiceGroupCaptureRequest,
            request: Request,
        ) -> RxMerServiceGroupCaptureResponse:
            """
            **Serving Group RxMER Capture**

            Executes concurrent RxMER capture for a single serving group using PyPNM.
            """
            base_url = str(request.base_url).rstrip("/")
            pypnm_base_url = f"{base_url}/cm"
            return await self._service.capture(payload, pypnm_base_url)


router = RxMerRouter().router

__all__ = [
    "router",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.const_display.schemas import (
    ConstDisplayServiceGroupCancelResponse,
    ConstDisplayServiceGroupOperationRequest,
    ConstDisplayServiceGroupResultsResponse,
    ConstDisplayServiceGroupStartCaptureRequest,
    ConstDisplayServiceGroupStartCaptureResponse,
    ConstDisplayServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.const_display.service import (
    ConstDisplayServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class ConstDisplayRouter:
    """
    FastAPI router for ConstDisplay orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/ofdm/constellationDisplay",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM OFDM ConstDisplay"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = ConstDisplayServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=ConstDisplayServiceGroupStartCaptureResponse,
            summary="Start SG-level ConstDisplay capture",
            description="Creates a filesystem-backed ConstDisplay operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: ConstDisplayServiceGroupStartCaptureRequest,
        ) -> ConstDisplayServiceGroupStartCaptureResponse:
            """
            **Serving Group ConstDisplay Start Capture**

            Creates a new SG-level ConstDisplay orchestration operation.
            """
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=ConstDisplayServiceGroupStatusResponse,
            summary="Get SG-level ConstDisplay status",
            description="Returns operation state for an ConstDisplay serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: ConstDisplayServiceGroupOperationRequest,
        ) -> ConstDisplayServiceGroupStatusResponse:
            """
            **Serving Group ConstDisplay Status**

            Returns the latest operation state for an SG-level ConstDisplay job.
            """
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=ConstDisplayServiceGroupResultsResponse,
            summary="Get SG-level ConstDisplay results",
            description="Returns linkage results for an ConstDisplay serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: ConstDisplayServiceGroupOperationRequest,
        ) -> ConstDisplayServiceGroupResultsResponse:
            """
            **Serving Group ConstDisplay Results**

            Returns summary and linkage records for an SG-level ConstDisplay job.
            """
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=ConstDisplayServiceGroupCancelResponse,
            summary="Cancel SG-level ConstDisplay capture",
            description="Requests cancellation for an ConstDisplay serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: ConstDisplayServiceGroupOperationRequest,
        ) -> ConstDisplayServiceGroupCancelResponse:
            """
            **Serving Group ConstDisplay Cancel**

            Requests cancellation for an SG-level ConstDisplay job.
            """
            return self._service.cancel(payload)


router = ConstDisplayRouter().router

__all__ = [
    "router",
]

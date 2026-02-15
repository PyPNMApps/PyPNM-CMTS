# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.us.ofdma.pre_equalization.schemas import (
    PreEqualizationServiceGroupCancelResponse,
    PreEqualizationServiceGroupOperationRequest,
    PreEqualizationServiceGroupResultsResponse,
    PreEqualizationServiceGroupStartCaptureRequest,
    PreEqualizationServiceGroupStartCaptureResponse,
    PreEqualizationServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.us.ofdma.pre_equalization.service import (
    PreEqualizationServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class PreEqualizationRouter:
    """
    FastAPI router for PreEqualization orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/us/ofdma/preEqualization",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM UPSTREAM OFDMA PreEqualization"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service = PreEqualizationServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=PreEqualizationServiceGroupStartCaptureResponse,
            summary="Start SG-level PreEqualization capture",
            description="Creates a filesystem-backed PreEqualization operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: PreEqualizationServiceGroupStartCaptureRequest,
        ) -> PreEqualizationServiceGroupStartCaptureResponse:
            """
            **Serving Group PreEqualization Start Capture**

            Creates a new SG-level PreEqualization orchestration operation.
            """
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=PreEqualizationServiceGroupStatusResponse,
            summary="Get SG-level PreEqualization status",
            description="Returns operation state for an PreEqualization serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: PreEqualizationServiceGroupOperationRequest,
        ) -> PreEqualizationServiceGroupStatusResponse:
            """
            **Serving Group PreEqualization Status**

            Returns the latest operation state for an SG-level PreEqualization job.
            """
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=PreEqualizationServiceGroupResultsResponse,
            summary="Get SG-level PreEqualization results",
            description="Returns linkage results for an PreEqualization serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: PreEqualizationServiceGroupOperationRequest,
        ) -> PreEqualizationServiceGroupResultsResponse:
            """
            **Serving Group PreEqualization Results**

            Returns summary and linkage records for an SG-level PreEqualization job.
            """
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=PreEqualizationServiceGroupCancelResponse,
            summary="Cancel SG-level PreEqualization capture",
            description="Requests cancellation for an PreEqualization serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: PreEqualizationServiceGroupOperationRequest,
        ) -> PreEqualizationServiceGroupCancelResponse:
            """
            **Serving Group PreEqualization Cancel**

            Requests cancellation for an SG-level PreEqualization job.
            """
            return self._service.cancel(payload)


router = PreEqualizationRouter().router

__all__ = [
    "router",
]

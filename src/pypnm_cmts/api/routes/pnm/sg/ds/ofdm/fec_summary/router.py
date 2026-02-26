# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.schemas import (
    FecSummaryServiceGroupCancelResponse,
    FecSummaryServiceGroupOperationRequest,
    FecSummaryServiceGroupResultsRequest,
    FecSummaryServiceGroupResultsResponse,
    FecSummaryServiceGroupStartCaptureRequest,
    FecSummaryServiceGroupStartCaptureResponse,
    FecSummaryServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.service import (
    FecSummaryServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class FecSummaryRouter:
    """
    FastAPI router for FecSummary orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/ofdm/fecSummary",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM OFDM FecSummary"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service = FecSummaryServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=FecSummaryServiceGroupStartCaptureResponse,
            summary="Start SG-level FecSummary capture",
            description="Creates a filesystem-backed FecSummary operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: FecSummaryServiceGroupStartCaptureRequest,
        ) -> FecSummaryServiceGroupStartCaptureResponse:
            """
            **Serving Group FecSummary Start Capture**

            Creates a new SG-level FecSummary orchestration operation.
            """
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=FecSummaryServiceGroupStatusResponse,
            summary="Get SG-level FecSummary status",
            description="Returns operation state for an FecSummary serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: FecSummaryServiceGroupOperationRequest,
        ) -> FecSummaryServiceGroupStatusResponse:
            """
            **Serving Group FecSummary Status**

            Returns the latest operation state for an SG-level FecSummary job.
            """
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=FecSummaryServiceGroupResultsResponse,
            summary="Get SG-level FecSummary results",
            description="Returns linkage results for an FecSummary serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: FecSummaryServiceGroupResultsRequest,
        ) -> FecSummaryServiceGroupResultsResponse:
            """
            **Serving Group FecSummary Results**

            Returns summary and linkage records for an SG-level FecSummary job.
            """
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=FecSummaryServiceGroupCancelResponse,
            summary="Cancel SG-level FecSummary capture",
            description="Requests cancellation for an FecSummary serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: FecSummaryServiceGroupOperationRequest,
        ) -> FecSummaryServiceGroupCancelResponse:
            """
            **Serving Group FecSummary Cancel**

            Requests cancellation for an SG-level FecSummary job.
            """
            return self._service.cancel(payload)


router = FecSummaryRouter().router

__all__ = [
    "router",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.histogram.schemas import (
    DsHistogramServiceGroupCancelResponse,
    DsHistogramServiceGroupOperationRequest,
    DsHistogramServiceGroupResultsResponse,
    DsHistogramServiceGroupStartCaptureRequest,
    DsHistogramServiceGroupStartCaptureResponse,
    DsHistogramServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.histogram.service import (
    DsHistogramServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class DsHistogramRouter:
    """FastAPI router for downstream Histogram orchestration endpoints."""

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/histogram",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM Histogram"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = DsHistogramServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=DsHistogramServiceGroupStartCaptureResponse,
            summary="Start SG-level downstream Histogram capture",
            description="Creates a filesystem-backed downstream Histogram operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: DsHistogramServiceGroupStartCaptureRequest,
        ) -> DsHistogramServiceGroupStartCaptureResponse:
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=DsHistogramServiceGroupStatusResponse,
            summary="Get SG-level downstream Histogram status",
            description="Returns operation state for a downstream Histogram serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: DsHistogramServiceGroupOperationRequest,
        ) -> DsHistogramServiceGroupStatusResponse:
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=DsHistogramServiceGroupResultsResponse,
            summary="Get SG-level downstream Histogram results",
            description="Returns linkage results for a downstream Histogram serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: DsHistogramServiceGroupOperationRequest,
        ) -> DsHistogramServiceGroupResultsResponse:
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=DsHistogramServiceGroupCancelResponse,
            summary="Cancel SG-level downstream Histogram capture",
            description="Requests cancellation for a downstream Histogram serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: DsHistogramServiceGroupOperationRequest,
        ) -> DsHistogramServiceGroupCancelResponse:
            return self._service.cancel(payload)


router = DsHistogramRouter().router

__all__ = [
    "router",
]

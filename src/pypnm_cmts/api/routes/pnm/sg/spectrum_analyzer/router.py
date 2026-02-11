# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.spectrum_analyzer.schemas import (
    SpectrumAnalyzerServiceGroupCancelResponse,
    SpectrumAnalyzerServiceGroupOperationRequest,
    SpectrumAnalyzerServiceGroupResultsResponse,
    SpectrumAnalyzerServiceGroupStartCaptureRequest,
    SpectrumAnalyzerServiceGroupStartCaptureResponse,
    SpectrumAnalyzerServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.spectrum_analyzer.service import (
    SpectrumAnalyzerServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class SpectrumAnalyzerRouter:
    """FastAPI router for full-bandwidth SpectrumAnalyzer orchestration endpoints."""

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/spectrumAnalyzer",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM SpectrumAnalyzer"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = SpectrumAnalyzerServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=SpectrumAnalyzerServiceGroupStartCaptureResponse,
            summary="Start SG-level SpectrumAnalyzer capture",
            description="Creates a filesystem-backed SpectrumAnalyzer operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: SpectrumAnalyzerServiceGroupStartCaptureRequest,
        ) -> SpectrumAnalyzerServiceGroupStartCaptureResponse:
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=SpectrumAnalyzerServiceGroupStatusResponse,
            summary="Get SG-level SpectrumAnalyzer status",
            description="Returns operation state for a SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: SpectrumAnalyzerServiceGroupOperationRequest,
        ) -> SpectrumAnalyzerServiceGroupStatusResponse:
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=SpectrumAnalyzerServiceGroupResultsResponse,
            summary="Get SG-level SpectrumAnalyzer results",
            description="Returns linkage results for a SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: SpectrumAnalyzerServiceGroupOperationRequest,
        ) -> SpectrumAnalyzerServiceGroupResultsResponse:
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=SpectrumAnalyzerServiceGroupCancelResponse,
            summary="Cancel SG-level SpectrumAnalyzer capture",
            description="Requests cancellation for a SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: SpectrumAnalyzerServiceGroupOperationRequest,
        ) -> SpectrumAnalyzerServiceGroupCancelResponse:
            return self._service.cancel(payload)


router = SpectrumAnalyzerRouter().router

__all__ = [
    "router",
]

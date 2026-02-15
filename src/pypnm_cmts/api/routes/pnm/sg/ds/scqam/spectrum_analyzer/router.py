# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.scqam.spectrum_analyzer.schemas import (
    ScQamSpectrumAnalyzerServiceGroupCancelResponse,
    ScQamSpectrumAnalyzerServiceGroupOperationRequest,
    ScQamSpectrumAnalyzerServiceGroupResultsResponse,
    ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest,
    ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse,
    ScQamSpectrumAnalyzerServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.scqam.spectrum_analyzer.service import (
    ScQamSpectrumAnalyzerServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class ScQamSpectrumAnalyzerRouter:
    """FastAPI router for downstream SCQAM SpectrumAnalyzer orchestration endpoints."""

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/scqam/spectrumAnalyzer",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM SCQAM SpectrumAnalyzer"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service = ScQamSpectrumAnalyzerServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse,
            summary="Start SG-level SCQAM SpectrumAnalyzer capture",
            description="Creates a filesystem-backed SCQAM SpectrumAnalyzer operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest,
        ) -> ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse:
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=ScQamSpectrumAnalyzerServiceGroupStatusResponse,
            summary="Get SG-level SCQAM SpectrumAnalyzer status",
            description="Returns operation state for an SCQAM SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: ScQamSpectrumAnalyzerServiceGroupOperationRequest,
        ) -> ScQamSpectrumAnalyzerServiceGroupStatusResponse:
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=ScQamSpectrumAnalyzerServiceGroupResultsResponse,
            summary="Get SG-level SCQAM SpectrumAnalyzer results",
            description="Returns linkage results for an SCQAM SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: ScQamSpectrumAnalyzerServiceGroupOperationRequest,
        ) -> ScQamSpectrumAnalyzerServiceGroupResultsResponse:
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=ScQamSpectrumAnalyzerServiceGroupCancelResponse,
            summary="Cancel SG-level SCQAM SpectrumAnalyzer capture",
            description="Requests cancellation for an SCQAM SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: ScQamSpectrumAnalyzerServiceGroupOperationRequest,
        ) -> ScQamSpectrumAnalyzerServiceGroupCancelResponse:
            return self._service.cancel(payload)


router = ScQamSpectrumAnalyzerRouter().router

__all__ = [
    "router",
]

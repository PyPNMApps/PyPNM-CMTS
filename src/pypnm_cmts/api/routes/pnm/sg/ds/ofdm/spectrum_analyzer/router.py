# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.spectrum_analyzer.schemas import (
    OfdmSpectrumAnalyzerServiceGroupCancelResponse,
    OfdmSpectrumAnalyzerServiceGroupOperationRequest,
    OfdmSpectrumAnalyzerServiceGroupResultsResponse,
    OfdmSpectrumAnalyzerServiceGroupStartCaptureRequest,
    OfdmSpectrumAnalyzerServiceGroupStartCaptureResponse,
    OfdmSpectrumAnalyzerServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.spectrum_analyzer.service import (
    OfdmSpectrumAnalyzerServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class OfdmSpectrumAnalyzerRouter:
    """FastAPI router for downstream OFDM SpectrumAnalyzer orchestration endpoints."""

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/ofdm/spectrumAnalyzer",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM OFDM SpectrumAnalyzer"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service = OfdmSpectrumAnalyzerServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=OfdmSpectrumAnalyzerServiceGroupStartCaptureResponse,
            summary="Start SG-level OFDM SpectrumAnalyzer capture",
            description="Creates a filesystem-backed OFDM SpectrumAnalyzer operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: OfdmSpectrumAnalyzerServiceGroupStartCaptureRequest,
        ) -> OfdmSpectrumAnalyzerServiceGroupStartCaptureResponse:
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=OfdmSpectrumAnalyzerServiceGroupStatusResponse,
            summary="Get SG-level OFDM SpectrumAnalyzer status",
            description="Returns operation state for an OFDM SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: OfdmSpectrumAnalyzerServiceGroupOperationRequest,
        ) -> OfdmSpectrumAnalyzerServiceGroupStatusResponse:
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=OfdmSpectrumAnalyzerServiceGroupResultsResponse,
            summary="Get SG-level OFDM SpectrumAnalyzer results",
            description="Returns linkage results for an OFDM SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: OfdmSpectrumAnalyzerServiceGroupOperationRequest,
        ) -> OfdmSpectrumAnalyzerServiceGroupResultsResponse:
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=OfdmSpectrumAnalyzerServiceGroupCancelResponse,
            summary="Cancel SG-level OFDM SpectrumAnalyzer capture",
            description="Requests cancellation for an OFDM SpectrumAnalyzer serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: OfdmSpectrumAnalyzerServiceGroupOperationRequest,
        ) -> OfdmSpectrumAnalyzerServiceGroupCancelResponse:
            return self._service.cancel(payload)


router = OfdmSpectrumAnalyzerRouter().router

__all__ = [
    "router",
]

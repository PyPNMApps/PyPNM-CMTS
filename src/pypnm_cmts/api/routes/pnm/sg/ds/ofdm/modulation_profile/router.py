# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.modulation_profile.schemas import (
    ModulationProfileServiceGroupCancelResponse,
    ModulationProfileServiceGroupOperationRequest,
    ModulationProfileServiceGroupResultsResponse,
    ModulationProfileServiceGroupStartCaptureRequest,
    ModulationProfileServiceGroupStartCaptureResponse,
    ModulationProfileServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.modulation_profile.service import (
    ModulationProfileServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class ModulationProfileRouter:
    """
    FastAPI router for ModulationProfile orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/ofdm/modulationProfile",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM OFDM ModulationProfile"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = ModulationProfileServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=ModulationProfileServiceGroupStartCaptureResponse,
            summary="Start SG-level ModulationProfile capture",
            description="Creates a filesystem-backed ModulationProfile operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: ModulationProfileServiceGroupStartCaptureRequest,
        ) -> ModulationProfileServiceGroupStartCaptureResponse:
            """
            **Serving Group ModulationProfile Start Capture**

            Creates a new SG-level ModulationProfile orchestration operation.
            """
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=ModulationProfileServiceGroupStatusResponse,
            summary="Get SG-level ModulationProfile status",
            description="Returns operation state for an ModulationProfile serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: ModulationProfileServiceGroupOperationRequest,
        ) -> ModulationProfileServiceGroupStatusResponse:
            """
            **Serving Group ModulationProfile Status**

            Returns the latest operation state for an SG-level ModulationProfile job.
            """
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=ModulationProfileServiceGroupResultsResponse,
            summary="Get SG-level ModulationProfile results",
            description="Returns linkage results for an ModulationProfile serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: ModulationProfileServiceGroupOperationRequest,
        ) -> ModulationProfileServiceGroupResultsResponse:
            """
            **Serving Group ModulationProfile Results**

            Returns summary and linkage records for an SG-level ModulationProfile job.
            """
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=ModulationProfileServiceGroupCancelResponse,
            summary="Cancel SG-level ModulationProfile capture",
            description="Requests cancellation for an ModulationProfile serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: ModulationProfileServiceGroupOperationRequest,
        ) -> ModulationProfileServiceGroupCancelResponse:
            """
            **Serving Group ModulationProfile Cancel**

            Requests cancellation for an SG-level ModulationProfile job.
            """
            return self._service.cancel(payload)


router = ModulationProfileRouter().router

__all__ = [
    "router",
]

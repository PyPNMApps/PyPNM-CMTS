# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.schemas import (
    RxMerServiceGroupCancelResponse,
    RxMerServiceGroupOperationRequest,
    RxMerServiceGroupResultsResponse,
    RxMerServiceGroupStartCaptureRequest,
    RxMerServiceGroupStartCaptureResponse,
    RxMerServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.service import RxMerServiceGroupOperationService
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class RxMerRouter:
    """
    FastAPI router for RxMER orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/ofdm/rxmer",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM OFDM RxMER"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = RxMerServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=RxMerServiceGroupStartCaptureResponse,
            summary="Start SG-level RxMER capture",
            description="Creates a filesystem-backed RxMER operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: RxMerServiceGroupStartCaptureRequest,
        ) -> RxMerServiceGroupStartCaptureResponse:
            """
            **Serving Group RxMER Start Capture**

            Creates a new SG-level RxMER orchestration operation.
            """
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=RxMerServiceGroupStatusResponse,
            summary="Get SG-level RxMER status",
            description="Returns operation state for an RxMER serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: RxMerServiceGroupOperationRequest,
        ) -> RxMerServiceGroupStatusResponse:
            """
            **Serving Group RxMER Status**

            Returns the latest operation state for an SG-level RxMER job.
            """
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=RxMerServiceGroupResultsResponse,
            summary="Get SG-level RxMER results",
            description="Returns linkage results for an RxMER serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: RxMerServiceGroupOperationRequest,
        ) -> RxMerServiceGroupResultsResponse:
            """
            **Serving Group RxMER Results**

            Returns summary and linkage records for an SG-level RxMER job.
            """
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=RxMerServiceGroupCancelResponse,
            summary="Cancel SG-level RxMER capture",
            description="Requests cancellation for an RxMER serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: RxMerServiceGroupOperationRequest,
        ) -> RxMerServiceGroupCancelResponse:
            """
            **Serving Group RxMER Cancel**

            Requests cancellation for an SG-level RxMER job.
            """
            return self._service.cancel(payload)


router = RxMerRouter().router

__all__ = [
    "router",
]

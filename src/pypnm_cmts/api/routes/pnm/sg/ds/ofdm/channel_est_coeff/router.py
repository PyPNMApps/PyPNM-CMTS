# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.channel_est_coeff.schemas import (
    ChannelEstCoeffServiceGroupCancelResponse,
    ChannelEstCoeffServiceGroupOperationRequest,
    ChannelEstCoeffServiceGroupResultsResponse,
    ChannelEstCoeffServiceGroupStartCaptureRequest,
    ChannelEstCoeffServiceGroupStartCaptureResponse,
    ChannelEstCoeffServiceGroupStatusResponse,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.channel_est_coeff.service import (
    ChannelEstCoeffServiceGroupOperationService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class ChannelEstCoeffRouter:
    """
    FastAPI router for ChannelEstCoeff orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/pnm/sg/ds/ofdm/channelEstCoeff",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS PNM DOWNSTREAM OFDM ChannelEstCoeff"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service = ChannelEstCoeffServiceGroupOperationService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/startCapture",
            response_model=ChannelEstCoeffServiceGroupStartCaptureResponse,
            summary="Start SG-level ChannelEstCoeff capture",
            description="Creates a filesystem-backed ChannelEstCoeff operation for serving groups.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def start_capture(
            payload: ChannelEstCoeffServiceGroupStartCaptureRequest,
        ) -> ChannelEstCoeffServiceGroupStartCaptureResponse:
            """
            **Serving Group ChannelEstCoeff Start Capture**

            Creates a new SG-level ChannelEstCoeff orchestration operation.
            """
            return self._service.start_capture(payload)

        @self.router.post(
            "/status",
            response_model=ChannelEstCoeffServiceGroupStatusResponse,
            summary="Get SG-level ChannelEstCoeff status",
            description="Returns operation state for an ChannelEstCoeff serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def status(
            payload: ChannelEstCoeffServiceGroupOperationRequest,
        ) -> ChannelEstCoeffServiceGroupStatusResponse:
            """
            **Serving Group ChannelEstCoeff Status**

            Returns the latest operation state for an SG-level ChannelEstCoeff job.
            """
            return self._service.status(payload)

        @self.router.post(
            "/results",
            response_model=ChannelEstCoeffServiceGroupResultsResponse,
            summary="Get SG-level ChannelEstCoeff results",
            description="Returns linkage results for an ChannelEstCoeff serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def results(
            payload: ChannelEstCoeffServiceGroupOperationRequest,
        ) -> ChannelEstCoeffServiceGroupResultsResponse:
            """
            **Serving Group ChannelEstCoeff Results**

            Returns summary and linkage records for an SG-level ChannelEstCoeff job.
            """
            return self._service.results(payload)

        @self.router.post(
            "/cancel",
            response_model=ChannelEstCoeffServiceGroupCancelResponse,
            summary="Cancel SG-level ChannelEstCoeff capture",
            description="Requests cancellation for an ChannelEstCoeff serving group job.",
            responses={**JSON_ONLY_FAST_API_RESPONSE},
        )
        def cancel(
            payload: ChannelEstCoeffServiceGroupOperationRequest,
        ) -> ChannelEstCoeffServiceGroupCancelResponse:
            """
            **Serving Group ChannelEstCoeff Cancel**

            Requests cancellation for an SG-level ChannelEstCoeff job.
            """
            return self._service.cancel(payload)


router = ChannelEstCoeffRouter().router

__all__ = [
    "router",
]

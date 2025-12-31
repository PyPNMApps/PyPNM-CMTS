# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import APIRouter
from starlette.responses import JSONResponse

from pypnm_cmts.api.routes.operational.schemas import (
    HealthResponseModel,
    OperationalStatusResponseModel,
    ReadyResponseModel,
    VersionResponseModel,
)
from pypnm_cmts.api.routes.operational.service import OperationalService
from pypnm_cmts.lib.constants import OperationalStatus


class OperationalRouter:
    """
    FastAPI router for operational endpoints.
    """

    def __init__(
        self,
        prefix: str = "/ops",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["Operational"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._service = OperationalService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/health",
            response_model=HealthResponseModel,
            summary="Operational health probe",
            description="Returns a basic liveness signal and runtime metadata.",
        )
        def health() -> HealthResponseModel:
            """
            **Operational Health**

            Returns liveness status and runtime identity metadata.
            """
            return self._service.health()

        @self.router.get(
            "/ready",
            response_model=ReadyResponseModel,
            summary="Operational readiness probe",
            description="Returns readiness based on local prerequisites.",
            responses={
                HTTPStatus.SERVICE_UNAVAILABLE.value: {
                    "model": ReadyResponseModel,
                    "description": "Not ready",
                }
            },
        )
        def ready() -> ReadyResponseModel:
            """
            **Operational Readiness**

            Validates local prerequisites for orchestration readiness.
            """
            ready_payload = self._service.ready()
            if ready_payload.status != OperationalStatus.OK:
                return JSONResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    content=ready_payload.model_dump(mode="json"),
                )
            return ready_payload

        @self.router.get(
            "/version",
            response_model=VersionResponseModel,
            summary="Operational version probe",
            description="Returns version and runtime metadata.",
        )
        def version() -> VersionResponseModel:
            """
            **Operational Version**

            Returns package and runtime version metadata.
            """
            return self._service.version()

        @self.router.get(
            "/status",
            response_model=OperationalStatusResponseModel,
            summary="Operational process status",
            description="Returns process and coordination snapshot metadata.",
        )
        def status() -> OperationalStatusResponseModel:
            """
            **Operational Status**

            Returns process status and coordination metadata.
            """
            return self._service.status()

router = OperationalRouter().router

__all__ = [
    "router",
]

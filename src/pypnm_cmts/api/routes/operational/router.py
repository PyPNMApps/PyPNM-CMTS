# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import APIRouter
from starlette.responses import JSONResponse

from pypnm_cmts.api.routes.operational.schemas import (
    HealthResponseModel,
    MemoryDetailResponseModel,
    OperationalStatusResponseModel,
    ReadyResponseModel,
    SgwPollIntervalResponseModel,
    SgwProcessResponseModel,
    SgwResetRequestModel,
    SgwResetResponseModel,
    SgwRestartRequestModel,
    SgwRestartResponseModel,
    VersionResponseModel,
)
from pypnm_cmts.api.routes.operational.service import OperationalService
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE
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
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        def health() -> HealthResponseModel:
            """
            **Operational Health**

            Returns liveness status and runtime identity metadata.
            """
            return self._service.health()

        @self.router.get(
            "/health/memoryDetail",
            response_model=MemoryDetailResponseModel,
            summary="Operational memory-detail probe",
            description="Returns lightweight process, SGW cache, and operation-store memory-debug counters.",
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        def memory_detail() -> MemoryDetailResponseModel:
            """
            **Operational Memory Detail**

            Returns lightweight counters to help explain process RSS growth.
            """
            return self._service.memory_detail()

        @self.router.get(
            "/ready",
            response_model=ReadyResponseModel,
            summary="Operational readiness probe",
            description="Returns readiness based on local prerequisites.",
            responses={
                **JSON_ONLY_FAST_API_RESPONSE,
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
            responses=JSON_ONLY_FAST_API_RESPONSE,
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
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        def status() -> OperationalStatusResponseModel:
            """
            **Operational Status**

            Returns process status and coordination metadata.
            """
            return self._service.status()

        @self.router.get(
            "/servingGroupWorker/process",
            response_model=SgwProcessResponseModel,
            summary="SGW worker process status",
            description="Returns SGW worker identifiers with uptime details.",
            responses={
                **JSON_ONLY_FAST_API_RESPONSE,
                HTTPStatus.SERVICE_UNAVAILABLE.value: {
                    "model": SgwProcessResponseModel,
                    "description": "SGW runtime unavailable",
                }
            },
        )
        def sgw_process() -> SgwProcessResponseModel:
            """
            **SGW Process**

            Returns worker identifiers with uptime details.
            """
            payload = self._service.sgw_process()
            if payload.status != OperationalStatus.OK:
                return JSONResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    content=payload.model_dump(mode="json"),
                )
            return payload

        @self.router.get(
            "/servingGroupWorker/poll-interval",
            response_model=SgwPollIntervalResponseModel,
            summary="SGW poll interval summary",
            description="Returns SGW poll intervals with refresh counters.",
            responses={
                **JSON_ONLY_FAST_API_RESPONSE,
                HTTPStatus.SERVICE_UNAVAILABLE.value: {
                    "model": SgwPollIntervalResponseModel,
                    "description": "SGW runtime unavailable",
                }
            },
        )
        def sgw_poll_interval() -> SgwPollIntervalResponseModel:
            """
            **SGW Poll Interval**

            Returns poll intervals with refresh counts per worker.
            """
            payload = self._service.sgw_poll_intervals()
            if payload.status != OperationalStatus.OK:
                return JSONResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    content=payload.model_dump(mode="json"),
                )
            return payload

        @self.router.post(
            "/servingGroupWorker/restart",
            response_model=SgwRestartResponseModel,
            summary="Queue a heavy SGW refresh",
            description="Queues a heavy refresh for the specified worker id.",
            responses={
                **JSON_ONLY_FAST_API_RESPONSE,
                HTTPStatus.SERVICE_UNAVAILABLE.value: {
                    "model": SgwRestartResponseModel,
                    "description": "SGW runtime unavailable or request rejected",
                }
            },
        )
        def sgw_restart(payload: SgwRestartRequestModel) -> SgwRestartResponseModel:
            """
            **SGW Restart**

            Queues a heavy refresh for the specified worker.
            """
            response = self._service.sgw_restart(payload)
            if response.status != OperationalStatus.OK:
                return JSONResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    content=response.model_dump(mode="json"),
                )
            return response

        @self.router.post(
            "/servingGroupWorker/resetCounters",
            response_model=SgwResetResponseModel,
            summary="Reset SGW refresh counters",
            description="Resets heavy/light refresh counters for the specified worker id.",
            responses={
                **JSON_ONLY_FAST_API_RESPONSE,
                HTTPStatus.SERVICE_UNAVAILABLE.value: {
                    "model": SgwResetResponseModel,
                    "description": "SGW runtime unavailable or request rejected",
                }
            },
        )
        def sgw_reset(payload: SgwResetRequestModel) -> SgwResetResponseModel:
            """
            **SGW Reset**

            Resets refresh counters for the specified worker.
            """
            response = self._service.sgw_reset(payload)
            if response.status != OperationalStatus.OK:
                return JSONResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    content=response.model_dump(mode="json"),
                )
            return response

router = OperationalRouter().router

__all__ = [
    "router",
]

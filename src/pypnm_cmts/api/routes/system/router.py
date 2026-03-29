# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from enum import Enum
from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from pypnm_cmts.api.routes.system.schemas import (
    CmtsSysDescrRequest,
    CmtsSysDescrResponse,
    CmtsWebServiceReloadResponse,
)
from pypnm_cmts.api.routes.system.service import (
    SystemCmtsSnmpService,
    SystemWebServiceControlService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class SystemRouter:
    """
    FastAPI router for CMTS system endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/system",
        tags: list[str | Enum] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS System"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/sysDescr",
            response_model=CmtsSysDescrResponse,
            summary="Retrieve CMTS sysDescr",
            description="Fetches the system description from a CMTS.",
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        async def get_sysdescr() -> CmtsSysDescrResponse:
            """
            **Retrieve CMTS System Description**

            This endpoint performs an SNMP query to fetch the system description (`sysDescr`) from
            a CMTS and parses it into a structured model.
            """
            try:
                request = CmtsSysDescrRequest()
                return await SystemCmtsSnmpService.get_sysdescr(request)
            except Exception as exc:
                self.logger.error(f"CMTS sysDescr error: {exc}")
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve CMTS sysDescr.",
                ) from exc

        @self.router.post(
            "/webService/reload",
            response_model=CmtsWebServiceReloadResponse,
            summary="Request CMTS web-service reload",
            description="Writes the configured reload sentinel file so an external watcher can restart the web service.",
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        def request_web_service_reload() -> CmtsWebServiceReloadResponse:
            """
            **Request CMTS Web-Service Reload**

            This endpoint does not restart the API process directly. It writes a configured
            sentinel file that an external watcher or supervisor must observe and act on.
            """
            try:
                return SystemWebServiceControlService.request_reload()
            except Exception as exc:
                self.logger.error(f"CMTS web-service reload request failed: {exc}", exc_info=True)
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Failed to request CMTS web-service reload.",
                ) from exc

router = SystemRouter().router

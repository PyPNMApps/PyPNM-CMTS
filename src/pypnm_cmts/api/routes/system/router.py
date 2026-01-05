# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from enum import Enum
from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from pypnm.lib.fastapi_constants import FAST_API_RESPONSE

from pypnm_cmts.api.routes.system.schemas import (
    CmtsSysDescrRequest,
    CmtsSysDescrResponse,
)
from pypnm_cmts.api.routes.system.service import SystemCmtsSnmpService


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
        self.logger = logging.getLogger(__name__)
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/sysDescr",
            response_model=CmtsSysDescrResponse,
            summary="Retrieve CMTS sysDescr",
            description="Fetches the system description from a CMTS.",
            responses=FAST_API_RESPONSE,
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

router = SystemRouter().router

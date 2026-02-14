# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter

from pypnm_cmts.api.routes.serving_group.cm.operations.schemas import (
    ServingGroupDocsDevResetNowRequest,
    ServingGroupDocsDevResetNowResponse,
)
from pypnm_cmts.api.routes.serving_group.cm.operations.service import (
    ServingGroupCableModemOperationsService,
)
from pypnm_cmts.api.utils.fastapi_responses import JSON_ONLY_FAST_API_RESPONSE


class ServingGroupCableModemOperationsRouter:
    """FastAPI router for serving-group cable modem operation endpoints."""

    def __init__(
        self,
        prefix: str = "/cmts/servingGroup/cableModem/operations",
        tags: list[str | Enum] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS Serving Group CableModem Operations"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = ServingGroupCableModemOperationsService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/docsDevResetNow",
            response_model=ServingGroupDocsDevResetNowResponse,
            summary="Issue docsDevResetNow for serving-group cable modems",
            description="Resolves serving-group and cable-modem scope, then sends docsDevResetNow SNMP commands.",
            responses=JSON_ONLY_FAST_API_RESPONSE,
        )
        def docs_dev_reset_now(
            request: ServingGroupDocsDevResetNowRequest,
        ) -> ServingGroupDocsDevResetNowResponse:
            """
            **Serving Group docsDevResetNow**

            Sends docsDevResetNow reset commands for resolved cable modems in scope.
            """
            return self._service.docs_dev_reset_now(request)


router = ServingGroupCableModemOperationsRouter().router

__all__ = [
    "router",
]

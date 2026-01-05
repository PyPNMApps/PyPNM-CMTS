# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter

from pypnm_cmts.api.routes.serving_group.schemas import (
    GetServingGroupCableModemsRequest,
    GetServingGroupCableModemsResponse,
    GetServingGroupIdsResponse,
    GetServingGroupTopologyRequest,
    GetServingGroupTopologyResponse,
    ServingGroupStatusResponse,
)
from pypnm_cmts.api.routes.serving_group.service import ServingGroupCacheService


class ServingGroupRouter:
    """
    FastAPI router for cache-backed serving group endpoints.
    """

    def __init__(
        self,
        prefix: str = "/cmts/servingGroup",
        tags: list[str | Enum] | None = None,
    ) -> None:
        if tags is None:
            tags = ["CMTS Serving Group"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._service = ServingGroupCacheService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/get/ids",
            response_model=GetServingGroupIdsResponse,
            summary="Retrieve discovered serving group ids",
            description="Returns discovered serving group ids and cache summaries.",
        )
        def get_ids() -> GetServingGroupIdsResponse:
            """
            **Serving Group Ids**

            Returns discovered SG ids and cache readiness metadata.
            """
            return self._service.get_ids()

        @self.router.get(
            "/status",
            response_model=ServingGroupStatusResponse,
            summary="Serving group worker status",
            description="Returns SGW startup status and cache readiness.",
        )
        def get_status() -> ServingGroupStatusResponse:
            """
            **Serving Group Status**

            Returns SGW startup status and cache readiness metadata.
            """
            return self._service.get_status()

        @self.router.post(
            "/get/cableModems",
            response_model=GetServingGroupCableModemsResponse,
            summary="Retrieve cable modems for a serving group",
            description="Returns cached cable modem membership for a serving group.",
        )
        def get_cable_modems(
            request: GetServingGroupCableModemsRequest,
        ) -> GetServingGroupCableModemsResponse:
            """
            **Serving Group Cable Modems**

            Returns a paged list of cable modems for the specified service group.
            """
            return self._service.get_cable_modems(request)

        @self.router.post(
            "/get/topology",
            response_model=GetServingGroupTopologyResponse,
            summary="Retrieve serving group topology",
            description="Returns cached topology summary for a serving group.",
        )
        def get_topology(
            request: GetServingGroupTopologyRequest,
        ) -> GetServingGroupTopologyResponse:
            """
            **Serving Group Topology**

            Returns cached topology summary for the specified service group.
            """
            return self._service.get_topology(request)


router = ServingGroupRouter().router

__all__ = [
    "router",
]

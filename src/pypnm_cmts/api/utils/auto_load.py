# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from fastapi import FastAPI

from pypnm_cmts.api.routes.operational.router import router as operational_router
from pypnm_cmts.api.routes.orchestrator.router import router as orchestrator_router
from pypnm_cmts.api.routes.serving_group.router import router as serving_group_router
from pypnm_cmts.api.routes.system.router import router as system_router


class RouterRegistrar:
    """Register API routers for the PyPNM-CMTS FastAPI app."""

    def register(self, app: FastAPI) -> FastAPI:
        """Attach API routers to the FastAPI application."""
        app.include_router(operational_router)
        app.include_router(orchestrator_router)
        app.include_router(serving_group_router)
        app.include_router(system_router)
        return app

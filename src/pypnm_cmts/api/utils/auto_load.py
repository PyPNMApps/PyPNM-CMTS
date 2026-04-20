# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

from fastapi import FastAPI

from pypnm_cmts.api.routes.debug.router import router as debug_router
from pypnm_cmts.api.routes.operational.router import router as operational_router
from pypnm_cmts.api.routes.orchestrator.router import router as orchestrator_router
from pypnm_cmts.api.routes.pnm.router import router as pnm_router
from pypnm_cmts.api.routes.serving_group.cm.operations.router import (
    router as serving_group_cm_operations_router,
)
from pypnm_cmts.api.routes.serving_group.operations.router import (
    router as serving_group_router,
)
from pypnm_cmts.api.routes.system.router import router as system_router
from pypnm_cmts.config.runtime_flags import ENV_DEBUG_MODE, is_env_flag_enabled


class RouterRegistrar:
    """Register API routers for the PyPNM-CMTS FastAPI app."""

    def register(self, app: FastAPI) -> FastAPI:
        """Attach API routers to the FastAPI application."""
        app.include_router(operational_router)
        if is_env_flag_enabled(ENV_DEBUG_MODE):
            app.include_router(debug_router)
        app.include_router(orchestrator_router)
        app.include_router(pnm_router)
        app.include_router(serving_group_router)
        app.include_router(serving_group_cm_operations_router)
        app.include_router(system_router)
        return app

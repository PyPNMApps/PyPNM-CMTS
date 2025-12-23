# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from fastapi import FastAPI

from pypnm_cmts.api.routes.system.router import router as system_router


class RouterRegistrar:
    """Register API routers for the PyPNM-CMTS FastAPI app."""

    def register(self, app: FastAPI) -> FastAPI:
        """Attach API routers to the FastAPI application."""
        app.include_router(system_router)
        return app

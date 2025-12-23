# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from fastapi import FastAPI


class RouterRegistrar:
    """Register API routers for the PyPNM-CMTS FastAPI app."""

    def register(self, app: FastAPI) -> FastAPI:
        """Attach API routers to the FastAPI application."""
        return app

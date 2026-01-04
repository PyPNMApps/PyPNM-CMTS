# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os
import pathlib
import sys
from contextlib import asynccontextmanager
from inspect import isawaitable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pypnm.api.main import app as pypnm_app

from pypnm_cmts.api.utils.auto_load import RouterRegistrar
from pypnm_cmts.combined_mode import CombinedModeRunner, combined_mode_enabled
from pypnm_cmts.sgw.runtime_state import (
    start_sgw_background_refresh,
    stop_sgw_background_refresh,
)
from pypnm_cmts.sgw.startup import SgwStartupService
from pypnm_cmts.startup.startup import StartUp
from pypnm_cmts.version import __version__

GZIP_MIN_SIZE_BYTES = 100_000

project_root = pathlib.Path(__file__).resolve()
while project_root.name != "src" and project_root != project_root.parent:
    project_root = project_root.parent

if project_root.name == "src" and str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

StartUp.initialize()

fast_api_description = """
**CMTS Operations API for DOCSIS PNM Workflows**

PyPNM-CMTS extends the PyPNM toolkit with CMTS-focused automation and
operational helpers. Use these APIs to script CMTS telemetry collection,
validate configuration state, and drive PNM workflows across fleets.

**Core capabilities include:**
- CMTS inventory and topology context for PNM workflows
- CMTS-side configuration validation and guardrails
- Telemetry orchestration for DOCSIS PNM capture workflows
- CMTS-focused reporting and operational checks

[**PyPNM Homepage**](https://github.com/PyPNMApps/PyPNM-CMTS)
"""

_combined_runner: CombinedModeRunner | None = None
_sgw_startup_service = SgwStartupService()


def _pytest_running() -> bool:
    return os.getenv("PYTEST_CURRENT_TEST") is not None


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> object:
    global _combined_runner
    if _combined_runner is None and combined_mode_enabled():
        _combined_runner = CombinedModeRunner()
    if _combined_runner is not None:
        _combined_runner.start()
    init_result = _sgw_startup_service.initialize()
    if isawaitable(init_result):
        await init_result
    started_refresh = False
    if not _pytest_running():
        started_refresh = start_sgw_background_refresh()
    try:
        yield
    finally:
        if started_refresh:
            stop_sgw_background_refresh()
        if _combined_runner is not None:
            _combined_runner.stop()


app = FastAPI(
    title="PyPNM-CMTS REST API",
    version=__version__,
    description=fast_api_description,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

app.include_router(pypnm_app.router, prefix="/pypnm")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Lightweight health endpoint for probes."""
    return {"status": "ok", "version": __version__}

app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_SIZE_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RouterRegistrar().register(app)

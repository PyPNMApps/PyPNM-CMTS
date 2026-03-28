# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from inspect import isawaitable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute
from pypnm.api.main import app as pypnm_app
from pypnm.version import __version__ as pypnm_version
from starlette.requests import Request
from starlette.responses import JSONResponse

from pypnm_cmts.api.health import CmtsHealthService, HealthResponseModel
from pypnm_cmts.api.utils.auto_load import RouterRegistrar
from pypnm_cmts.combined_mode import CombinedModeRunner, combined_mode_enabled
from pypnm_cmts.config.runtime_flags import (
    ENV_MUTE_PYPNM_ENDPOINTS,
    ENV_MUTE_TAGS,
    ENV_MUTE_TAGS_HARD,
    is_env_flag_enabled,
    read_env_csv_set,
)
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

version = __version__

fast_api_description = f"""
**CMTS Operations API for DOCSIS PNM Workflows**

PyPNM-CMTS extends the PyPNM toolkit with CMTS-focused automation and
operational helpers. Use these APIs to script CMTS telemetry collection,
validate configuration state, and drive PNM workflows across fleets.

**Core capabilities include:**
- CMTS inventory and topology context for PNM workflows
- CMTS-side configuration validation and guardrails
- Telemetry orchestration for DOCSIS PNM capture workflows
- CMTS-focused reporting and operational checks

| HomePage | PyPi Package | Version |
|----------|--------------|---------|
| [PyPNM](https://github.com/PyPNMApps/PyPNM)           | [pypnm-docsis](https://pypi.org/project/pypnm-docsis)             | {pypnm_version}   |
| [PyPNM-CMTS](https://github.com/PyPNMApps/PyPNM-CMTS) | [pypnm-docsis-cmts](https://pypi.org/project/pypnm-docsis-cmts)   | {version}         |
| [PyPNM-PMA](https://github.com/PyPNMApps/PyPNM-PMA)   | [pypnm-docsis-pma](https://pypi.org/project/pypnm-docsis-pma)     | Not-Installed     |

"""

_combined_runner: CombinedModeRunner | None = None
_sgw_startup_service = SgwStartupService()
_health_service = CmtsHealthService()
_hard_muted_routes: list[APIRoute] = []


def _pytest_running() -> bool:
    return os.getenv("PYTEST_CURRENT_TEST") is not None


def _route_tag_set(route: APIRoute) -> set[str]:
    tags = route.tags or []
    return {str(tag).strip().lower() for tag in tags if str(tag).strip() != ""}


def _apply_muted_tag_policy(app_instance: FastAPI) -> None:
    _hard_muted_routes.clear()
    muted_tags = read_env_csv_set(ENV_MUTE_TAGS)
    if not muted_tags:
        return

    hard_mute = is_env_flag_enabled(ENV_MUTE_TAGS_HARD)
    for route in app_instance.router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not (_route_tag_set(route) & muted_tags):
            continue
        route.include_in_schema = False
        if hard_mute:
            _hard_muted_routes.append(route)


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

if not is_env_flag_enabled(ENV_MUTE_PYPNM_ENDPOINTS):
    app.include_router(pypnm_app.router, prefix="/cm")


@app.get("/health", tags=["Health"], response_model=HealthResponseModel)
def health() -> HealthResponseModel:
    """CMTS health endpoint for probes and WebUI status integration."""
    return _health_service.build_response(__version__)

app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_SIZE_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RouterRegistrar().register(app)
_apply_muted_tag_policy(app)


@app.middleware("http")
async def _deny_hard_muted_tag_routes(
    request: Request,
    call_next: Callable[[Request], Awaitable[object]],
) -> JSONResponse | object:
    if _hard_muted_routes:
        for route in _hard_muted_routes:
            methods = route.methods or set()
            if request.method.upper() not in methods:
                continue
            if route.path_regex.fullmatch(request.scope["path"]) is None:
                continue
            return JSONResponse(
                status_code=403,
                content={"detail": "Endpoint disabled by policy"},
                headers={"X-Endpoint-Policy": "muted-tag"},
            )
    return await call_next(request)

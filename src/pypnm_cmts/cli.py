#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import argparse
import os
import sys

import uvicorn

from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__

SUCCESS_EXIT_CODE = 0
HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 8000
LOG_LEVEL_DEFAULT = "info"
DEFAULT_WORKERS = 1
TIMEOUT_KEEP_ALIVE_SECONDS = 120


def main() -> int:
    """
    Launch the PyPNM-CMTS FastAPI service with optional HTTPS support.

    Returns:
        int: Process exit code.
    """
    return _run_cli()


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Launch the PyPNM-CMTS FastAPI service with optional HTTPS support."
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__version__}",
        help="Show PyPNM-CMTS version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Select orchestrator execution mode.")
    run_parser.add_argument(
        "--mode",
        choices=[mode.value for mode in OrchestratorMode],
        required=True,
        help="Execution mode: standalone, controller, or worker.",
    )
    run_parser.add_argument(
        "--config",
        default="",
        help="Optional path to system.json configuration file.",
    )
    run_parser.add_argument(
        "--sg-id",
        default="",
        help="Service group identifier (required for worker mode).",
    )

    parser.add_argument("--host", default=HOST_DEFAULT, help=f"Host to bind (default: {HOST_DEFAULT})")
    parser.add_argument("--port", default=PORT_DEFAULT, type=int, help=f"Port to bind (default: {PORT_DEFAULT})")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS (requires cert and key)")
    parser.add_argument("--cert", default="./certs/cert.pem", help="Path to SSL certificate")
    parser.add_argument("--key", default="./certs/key.pem", help="Path to SSL private key")

    parser.add_argument(
        "--log-level",
        default=LOG_LEVEL_DEFAULT,
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info).",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of worker processes (default: 1).",
    )

    parser.add_argument(
        "--no-access-log",
        action="store_true",
        help="Disable Uvicorn access log.",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on file changes (dev only).",
    )

    parser.add_argument(
        "--reload-dir",
        dest="reload_dirs",
        action="append",
        default=[],
        help="Directory to watch for changes. Can be passed multiple times. Default: src (when --reload)",
    )

    parser.add_argument(
        "--reload-include",
        dest="reload_includes",
        action="append",
        default=["*.py"],
        help="Glob pattern(s) to include for reload. Can be passed multiple times. Default: *.py",
    )

    parser.add_argument(
        "--reload-exclude",
        dest="reload_excludes",
        action="append",
        default=["*.pyc", "*__pycache__*", "*.tmp", "*.log"],
        help="Glob pattern(s) to exclude from reload. Can be passed multiple times.",
    )
    return parser


def _run_cli() -> int:
    """
    Execute the CLI with Phase-0 run-mode parsing.
    """
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        mode_value = OrchestratorMode(args.mode)
        if mode_value == OrchestratorMode.WORKER and args.sg_id == "":
            print("ERROR: --sg-id is required when mode=worker.", file=sys.stderr)
            return 2
        if mode_value == OrchestratorMode.STANDALONE:
            print("Mode standalone is wired but not implemented (Phase-1).")
        elif mode_value == OrchestratorMode.CONTROLLER:
            print("Mode controller is wired but not implemented (Phase-1).")
        elif mode_value == OrchestratorMode.WORKER:
            print("Mode worker is wired but not implemented (Phase-1).")
        return SUCCESS_EXIT_CODE

    if args.ssl:
        print(f"🔒 Launching FastAPI with HTTPS on https://{args.host}:{args.port}")
    else:
        print(f"🌐 Launching FastAPI with HTTP on http://{args.host}:{args.port}")

    os.environ["PYTHONPATH"] = os.getcwd() + "/src:" + os.environ.get("PYTHONPATH", "")

    uvicorn_args = {
        "app": "pypnm_cmts.api.main:app",
        "host": args.host,
        "port": args.port,
        "timeout_keep_alive": TIMEOUT_KEEP_ALIVE_SECONDS,
        "log_level": args.log_level,
        "workers": args.workers,
        "access_log": not args.no_access_log,
    }

    if args.reload:
        if args.workers != DEFAULT_WORKERS:
            print("[WARN] --workers is ignored when --reload is enabled; using workers=1 for dev reload.")
            uvicorn_args["workers"] = DEFAULT_WORKERS

        reload_dirs = args.reload_dirs or ["src"]
        uvicorn_args.update(
            {
                "reload": True,
                "reload_dirs": reload_dirs,
                "reload_includes": args.reload_includes,
                "reload_excludes": args.reload_excludes,
            }
        )
        print(f"🔁 Auto-reload enabled. Watching: {', '.join(reload_dirs)}")

    if args.ssl:
        uvicorn_args.update(
            {
                "ssl_certfile": args.cert,
                "ssl_keyfile": args.key,
            }
        )

    uvicorn.run(**uvicorn_args)

    return SUCCESS_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())

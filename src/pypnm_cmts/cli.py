#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from pypnm_cmts.lib.types import CoordinationElectionName, OwnerId, ServiceGroupId
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.orchestrator.models import OrchestratorRunResultModel
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__

SUCCESS_EXIT_CODE = 0
EXIT_CODE_USAGE = 2
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


def _add_run_mode_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in OrchestratorMode],
        required=True,
        help="Execution mode: standalone, controller, or worker.",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Optional path to system.json configuration file.",
    )
    parser.add_argument(
        "--sg-id",
        default="",
        help="Service group identifier (required for worker mode).",
    )
    parser.add_argument(
        "--owner-id",
        default="",
        help="Optional owner id override for coordination.",
    )
    parser.add_argument(
        "--target-service-groups",
        type=int,
        default=None,
        help="Optional target service groups override.",
    )
    parser.add_argument(
        "--shard-mode",
        default=None,
        choices=["sequential", "score"],
        help="Shard mode override: sequential or score.",
    )
    parser.add_argument(
        "--tick-interval-seconds",
        type=float,
        default=None,
        help="Optional tick interval override (seconds).",
    )
    parser.add_argument(
        "--leader-ttl-seconds",
        type=int,
        default=None,
        help="Optional leader TTL override (seconds).",
    )
    parser.add_argument(
        "--lease-ttl-seconds",
        type=int,
        default=None,
        help="Optional lease TTL override (seconds).",
    )
    parser.add_argument(
        "--state-dir",
        default="",
        help="Optional coordination state directory override.",
    )
    parser.add_argument(
        "--election-name",
        default="",
        help="Optional election name override.",
    )


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

    run_parser = subparsers.add_parser("run", help="Run a single orchestrator tick and print JSON output.")
    _add_run_mode_args(run_parser)

    run_forever_parser = subparsers.add_parser("run-forever", help="Run orchestrator ticks continuously and print JSON output.")
    _add_run_mode_args(run_forever_parser)
    run_forever_parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Optional maximum number of ticks to execute.",
    )

    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI service (Uvicorn).")
    serve_parser.add_argument("--host", default=HOST_DEFAULT, help=f"Host to bind (default: {HOST_DEFAULT})")
    serve_parser.add_argument("--port", default=PORT_DEFAULT, type=int, help=f"Port to bind (default: {PORT_DEFAULT})")
    serve_parser.add_argument("--ssl", action="store_true", help="Enable HTTPS (requires cert and key)")
    serve_parser.add_argument("--cert", default="./certs/cert.pem", help="Path to SSL certificate")
    serve_parser.add_argument("--key", default="./certs/key.pem", help="Path to SSL private key")

    serve_parser.add_argument(
        "--log-level",
        default=LOG_LEVEL_DEFAULT,
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info).",
    )

    serve_parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of worker processes (default: 1).",
    )

    serve_parser.add_argument(
        "--no-access-log",
        action="store_true",
        help="Disable Uvicorn access log.",
    )

    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on file changes (dev only).",
    )

    serve_parser.add_argument(
        "--reload-dir",
        dest="reload_dirs",
        action="append",
        default=[],
        help="Directory to watch for changes. Can be passed multiple times. Default: src (when --reload)",
    )

    serve_parser.add_argument(
        "--reload-include",
        dest="reload_includes",
        action="append",
        default=["*.py"],
        help="Glob pattern(s) to include for reload. Can be passed multiple times. Default: *.py",
    )

    serve_parser.add_argument(
        "--reload-exclude",
        dest="reload_excludes",
        action="append",
        default=["*.pyc", "*__pycache__*", "*.tmp", "*.log"],
        help="Glob pattern(s) to exclude from reload. Can be passed multiple times.",
    )

    return parser


def _build_launcher(args: argparse.Namespace) -> CmtsOrchestratorLauncher:
    config_value = args.config
    sg_id_value = args.sg_id
    owner_id_value = args.owner_id
    state_dir_value = args.state_dir
    election_name_value = args.election_name

    mode_value = OrchestratorMode(args.mode)
    if mode_value == OrchestratorMode.WORKER and sg_id_value == "":
        raise ValueError("--sg-id is required when mode=worker.")

    config_path: Path | None = Path(config_value) if config_value != "" else None
    state_dir: Path | None = Path(state_dir_value) if state_dir_value != "" else None
    sg_id: ServiceGroupId | None = None
    if sg_id_value != "":
        sg_id = CmtsOrchestratorLauncher._parse_sg_id(sg_id_value)
    owner_id: OwnerId | None = OwnerId(owner_id_value) if owner_id_value != "" else None
    election_name: CoordinationElectionName | None = None
    if election_name_value != "":
        election_name = CoordinationElectionName(election_name_value)

    return CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=mode_value,
        sg_id=sg_id,
        owner_id=owner_id,
        target_service_groups=args.target_service_groups,
        shard_mode=args.shard_mode,
        tick_interval_seconds=args.tick_interval_seconds,
        leader_ttl_seconds=args.leader_ttl_seconds,
        lease_ttl_seconds=args.lease_ttl_seconds,
        state_dir=state_dir,
        election_name=election_name,
    )


def _run_cli() -> int:
    """
    Execute the CLI.
    """
    parser = _build_parser()
    args = parser.parse_args()

    if args.command in {"run", "run-forever"}:
        try:
            launcher = _build_launcher(args)
        except ValidationError as exc:
            _print_validation_errors(exc)
            return EXIT_CODE_USAGE
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return EXIT_CODE_USAGE

        if args.command == "run":
            try:
                result = launcher.run_once()
            except ValidationError as exc:
                _print_validation_errors(exc)
                return EXIT_CODE_USAGE
            except ValueError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return EXIT_CODE_USAGE
            print(result.model_dump_json(indent=2))
            return SUCCESS_EXIT_CODE

        def _print_tick(result: OrchestratorRunResultModel) -> None:
            print(result.model_dump_json())

        try:
            if args.max_ticks is not None and int(args.max_ticks) < 0:
                print("ERROR: --max-ticks must be non-negative.", file=sys.stderr)
                return EXIT_CODE_USAGE
            launcher.run_forever(on_tick=_print_tick, max_ticks=args.max_ticks)
        except ValidationError as exc:
            _print_validation_errors(exc)
            return EXIT_CODE_USAGE
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return EXIT_CODE_USAGE
        return SUCCESS_EXIT_CODE

    if args.command == "serve":
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

    parser.print_help()
    return EXIT_CODE_USAGE


def _print_validation_errors(exc: ValidationError) -> None:
    """
    Print concise validation errors to stderr.
    """
    errors = exc.errors()
    if not errors:
        print(f"ERROR: {exc}", file=sys.stderr)
        return
    for item in errors:
        loc = item.get("loc", ())
        msg = item.get("msg", "validation error")
        field_path = ".".join(str(part) for part in loc) if loc else "value"
        print(f"ERROR: {field_path}: {msg}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())

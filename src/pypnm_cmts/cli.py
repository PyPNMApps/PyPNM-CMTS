#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, TypeAlias

import uvicorn
from pydantic import ValidationError
from pypnm.lib.types import HostNameStr, SnmpReadCommunity, SnmpWriteCommunity
from pypnm.support import serve_background
from pypnm.support.worker_profile import (
    WorkerProfile,
    default_profile_env_path,
    detect_worker_profile,
    load_seeded_profile,
)

from pypnm_cmts.config.request_defaults import (
    ENV_CM_SNMPV2C_WRITE_COMMUNITY,
    ENV_CM_TFTP_IPV4,
    ENV_CM_TFTP_IPV6,
)
from pypnm_cmts.config.runtime_flags import (
    ENV_MUTE_PYPNM_ENDPOINTS,
    ENV_MUTE_TAGS,
    ENV_MUTE_TAGS_HARD,
)
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.support.reload_watcher import ensure_reload_watcher
from pypnm_cmts.support.serve_launch_state import build_launch_state, write_launch_state
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__

if TYPE_CHECKING:
    from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
    from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
    from pypnm_cmts.orchestrator.models import OrchestratorRunResultModel

SUCCESS_EXIT_CODE = 0
EXIT_CODE_USAGE = 2
EXIT_CODE_FAILURE = 1
EXIT_CODE_SIGINT = 130
HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 8080
LOG_LEVEL_DEFAULT = "info"
DEFAULT_WORKERS = 1
TIMEOUT_KEEP_ALIVE_SECONDS = 120
TIMEOUT_GRACEFUL_SHUTDOWN_SECONDS = 5
DEFAULT_LIMIT_MAX_REQUESTS = 0
DEFAULT_SNMP_PORT = 161
_DEPRECATED_CMTS_PORT_FLAG = "--cmts-port"
_SNMP_PORT_FLAG = "--snmp-port"
_cmts_port_warned = False
BACKGROUND_CHILD_ENV = serve_background.BACKGROUND_CHILD_ENV
BACKGROUND_PIDFILE_ENV = getattr(
    serve_background,
    "BACKGROUND_PIDFILE_ENV",
    "PYPNM_BACKGROUND_PIDFILE",
)
launch_background_serve = serve_background.launch_background_serve
_LaunchArgv: TypeAlias = list[str]
_LaunchCommand: TypeAlias = tuple[str, _LaunchArgv]


def _project_root() -> Path:
    """Return the PyPNM-CMTS project root (parent of ``src/``)."""
    return Path(__file__).resolve().parents[2]


def _sanitize_pythonpath_for_serve(project_root: Path | None = None) -> None:
    """Restrict serve-time PYTHONPATH to this repo's src directory."""
    root = project_root if project_root is not None else _project_root()
    src_path = str(root / "src")
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    existing_entries = [entry for entry in existing_pythonpath.split(os.pathsep) if entry.strip() != ""]

    filtered_sys_path: list[str] = []
    for entry in sys.path:
        if entry in existing_entries and entry != src_path:
            continue
        filtered_sys_path.append(entry)
    sys.path = filtered_sys_path

    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    os.environ["PYTHONPATH"] = src_path


def _prepare_runtime_paths_for_serve(args: argparse.Namespace) -> None:
    """Normalize serve-time user paths without changing the process cwd."""
    original_cwd = Path.cwd()
    project_root = _project_root()

    if hasattr(args, "cert") and isinstance(args.cert, str) and args.cert.strip() != "":
        cert_path = Path(args.cert)
        if not cert_path.is_absolute():
            args.cert = str((original_cwd / cert_path).resolve())

    if hasattr(args, "key") and isinstance(args.key, str) and args.key.strip() != "":
        key_path = Path(args.key)
        if not key_path.is_absolute():
            args.key = str((original_cwd / key_path).resolve())

    if hasattr(args, "reload_dirs") and isinstance(args.reload_dirs, list):
        resolved_reload_dirs: list[str] = []
        for entry in args.reload_dirs:
            entry_path = Path(str(entry))
            if entry_path.is_absolute():
                resolved_reload_dirs.append(str(entry_path))
                continue
            resolved_reload_dirs.append(str((original_cwd / entry_path).resolve()))
        args.reload_dirs = resolved_reload_dirs

    _sanitize_pythonpath_for_serve(project_root)


def _runtime_profile_selection_message(workers: int, limit_max_requests: int) -> str:
    """Build the serve-time runtime profile selection message."""
    source = os.environ.get("PYPNM_ACTIVE_RUNTIME_SOURCE", "explicit_cli")
    profile_env_path = os.environ.get("PYPNM_SERVE_ENV_FILE", str(default_profile_env_path()))

    if source == "seeded_profile":
        return (
            "Auto-selected FastAPI runtime profile: "
            f"workers={workers} limit_max_requests={limit_max_requests} "
            f"profile={profile_env_path}"
        )

    return (
        "FastAPI runtime profile: "
        f"workers={workers} limit_max_requests={limit_max_requests} "
        f"source={source} profile={profile_env_path}"
    )


def _log_runtime_profile_selection(workers: int, limit_max_requests: int) -> None:
    print(f"[INFO] {_runtime_profile_selection_message(workers, limit_max_requests)}")


def _record_background_parent_pid() -> None:
    if os.environ.get(BACKGROUND_CHILD_ENV) != "1":
        return
    pidfile = os.environ.get(BACKGROUND_PIDFILE_ENV, "").strip()
    if pidfile == "":
        return
    Path(pidfile).write_text(f"{os.getpid()}\n", encoding="utf-8")


def _current_launch_command() -> _LaunchCommand:
    """Return the best-effort command needed to relaunch the current serve process."""
    original_argv = [str(value) for value in getattr(sys, "orig_argv", []) if str(value).strip() != ""]
    if len(original_argv) >= 2:
        return sys.executable, original_argv[1:]

    argv0 = str(Path(sys.argv[0]).resolve())
    return sys.executable, [argv0, *[str(value) for value in sys.argv[1:]]]


def _resolve_runtime_worker_profile(args: argparse.Namespace) -> tuple[int, int]:
    profile_env_path = Path(os.environ.get("PYPNM_SERVE_ENV_FILE", str(default_profile_env_path())))

    if args.workers is not None and args.limit_max_requests is not None:
        os.environ["PYPNM_ACTIVE_RUNTIME_SOURCE"] = "explicit_cli"
        return args.workers, args.limit_max_requests

    profile: WorkerProfile | None = load_seeded_profile(profile_env_path)
    if profile is not None:
        os.environ["PYPNM_ACTIVE_RUNTIME_SOURCE"] = "seeded_profile"
    else:
        profile = detect_worker_profile()
        os.environ["PYPNM_ACTIVE_RUNTIME_SOURCE"] = "hardware_auto"

    workers = args.workers if args.workers is not None else profile.workers
    limit_max_requests = (
        args.limit_max_requests
        if args.limit_max_requests is not None
        else profile.limit_max_requests
    )
    return workers, limit_max_requests


def _sgw_enabled(settings: object) -> bool:
    sgw_settings = getattr(settings, "sgw", None)
    if sgw_settings is None:
        return False
    return bool(getattr(sgw_settings, "enabled", False))


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
        help="Execution mode: standalone (coordination only), controller (leader only), worker (lease + tests), combined (controller + worker).",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Optional path to system.json configuration file (defaults to built-in config).",
    )
    parser.add_argument(
        "--cmts-hostname",
        default="",
        help="Override adapter.hostname for discovery/runtime (IP or hostname).",
    )
    parser.add_argument(
        "--read-community",
        default="",
        help="Override adapter.community (SNMPv2c read community).",
    )
    parser.add_argument(
        "--write-community",
        default="",
        help="Override adapter.write_community (SNMPv2c write community).",
    )
    parser.add_argument(
        "--snmp-port",
        "--cmts-port",
        dest="snmp_port",
        type=int,
        default=None,
        help="Override adapter.port (SNMP port). --cmts-port is deprecated.",
    )
    parser.add_argument(
        "--sg-id",
        default="",
        help="Service group id for worker mode (required for bound workers).",
    )
    parser.add_argument(
        "--owner-id",
        default="",
        help="Override coordination owner id (affects leader/lease identity).",
    )
    parser.add_argument(
        "--target-service-groups",
        type=int,
        default=None,
        help="Override target service groups per replica (0 means all).",
    )
    parser.add_argument(
        "--shard-mode",
        default=None,
        choices=["sequential", "score"],
        help="Shard mode override: sequential (default) or score.",
    )
    parser.add_argument(
        "--tick-interval-seconds",
        type=float,
        default=None,
        help="Override tick interval in seconds (must be less than TTLs).",
    )
    parser.add_argument(
        "--leader-ttl-seconds",
        type=int,
        default=None,
        help="Override leader TTL in seconds.",
    )
    parser.add_argument(
        "--lease-ttl-seconds",
        type=int,
        default=None,
        help="Override service group lease TTL in seconds.",
    )
    parser.add_argument(
        "--state-dir",
        default="",
        help="Override coordination state directory.",
    )
    parser.add_argument(
        "--election-name",
        default="",
        help="Override leader election namespace.",
    )
    parser.add_argument(
        "--cm-snmpv2c-write-community",
        default="",
        help="Override CM SNMPv2c write community for request defaults.",
    )
    parser.add_argument(
        "--cm-tftp-ipv4",
        default="",
        help="Override CM TFTP IPv4 for request defaults.",
    )
    parser.add_argument(
        "--cm-tftp-ipv6",
        default="",
        help="Override CM TFTP IPv6 for request defaults.",
    )


def _add_discover_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cmts-hostname",
        default="",
        help="CMTS hostname or IP address (required if not in config).",
    )
    parser.add_argument(
        "--read-community",
        default="",
        help="SNMPv2c read community string (default: public).",
    )
    parser.add_argument(
        "--write-community",
        default="",
        help="Optional SNMPv2c write community (defaults to read community when empty).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_SNMP_PORT,
        help="SNMP port for discovery (default: 161).",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Optional path to system.json configuration file (defaults to built-in config).",
    )
    parser.add_argument(
        "--state-dir",
        default="",
        help="Override coordination state directory for snapshot persistence.",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Output in text format instead of JSON.",
    )


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        description="PyPNM-CMTS CLI for orchestration, discovery, and service operations.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  pypnm-cmts run --mode standalone\n"
            "  pypnm-cmts run --mode worker --sg-id 1\n"
            "  pypnm-cmts discover --cmts-hostname 192.168.0.100 --read-community public\n"
            "  pypnm-cmts run-forever --mode standalone --tick-interval-seconds 1 --max-ticks 5\n"
            "  pypnm-cmts serve --host 0.0.0.0 --port 8080\n"
            "  pypnm-cmts serve --reload\n"
            "\n"
            "Use \"pypnm-cmts <command> --help\" for command-specific options.\n"
            "Man page: docs/system/pypnm-cmts-manpage.md"
        ),
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
        help="Stop after N ticks (optional; for tests or bounded runs).",
    )

    discover_parser = subparsers.add_parser("discover", help="Discover CMTS service groups and registered cable modems.")
    _add_discover_args(discover_parser)

    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI service (Uvicorn).")
    serve_parser.add_argument("--host", default=HOST_DEFAULT, help=f"Host to bind (default: {HOST_DEFAULT})")
    serve_parser.add_argument("--port", default=PORT_DEFAULT, type=int, help=f"Port to bind (default: {PORT_DEFAULT})")
    serve_parser.add_argument("--ssl", action="store_true", help="Enable HTTPS (requires cert and key).")
    serve_parser.add_argument("--cert", default="./certs/cert.pem", help="Path to SSL certificate (PEM).")
    serve_parser.add_argument("--key", default="./certs/key.pem", help="Path to SSL private key (PEM).")
    serve_parser.add_argument(
        "--cmts-hostname",
        default="",
        help="Override adapter.hostname for SGW startup discovery.",
    )
    serve_parser.add_argument(
        "--read-community",
        default="",
        help="Override adapter.community for SGW startup discovery.",
    )
    serve_parser.add_argument(
        "--write-community",
        default="",
        help="Override adapter.write_community for SGW startup discovery.",
    )
    serve_parser.add_argument(
        "--cm-snmpv2c-write-community",
        default="",
        help="Override CM SNMPv2c write community for request defaults.",
    )
    serve_parser.add_argument(
        "--cm-tftp-ipv4",
        default="",
        help="Override CM TFTP IPv4 for request defaults.",
    )
    serve_parser.add_argument(
        "--cm-tftp-ipv6",
        default="",
        help="Override CM TFTP IPv6 for request defaults.",
    )
    serve_parser.add_argument(
        "--with-runner",
        action="store_true",
        help="Start the orchestrator runner in-process (combined mode).",
    )
    serve_parser.add_argument(
        "--mute-pypnm-endpoints",
        action="store_true",
        help="Suppress legacy PyPNM routes under /cm at startup.",
    )
    serve_parser.add_argument(
        "--mute-tags",
        default="",
        help="Comma-separated route tags to mute at startup (example: Orchestrator,Operational).",
    )
    serve_parser.add_argument(
        "--mute-tags-hard",
        action="store_true",
        help="When used with --mute-tags, enforce 403 for matching tagged routes.",
    )

    serve_parser.add_argument(
        "--log-level",
        default=LOG_LEVEL_DEFAULT,
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info).",
    )

    serve_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (default: auto-select from hardware profile).",
    )

    serve_parser.add_argument(
        "--limit-max-requests",
        type=int,
        default=None,
        help=(
            "Restart a worker after serving this many requests. "
            "Default: auto-select from hardware profile."
        ),
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
        help="Directory to watch for changes (repeatable). Default: src (when --reload).",
    )

    serve_parser.add_argument(
        "--reload-include",
        dest="reload_includes",
        action="append",
        default=["*.py"],
        help="Glob pattern(s) to include for reload (repeatable). Default: *.py.",
    )

    serve_parser.add_argument(
        "--reload-exclude",
        dest="reload_excludes",
        action="append",
        default=["*.pyc", "*__pycache__*", "*.tmp", "*.log"],
        help="Glob pattern(s) to exclude from reload (repeatable).",
    )
    serve_parser.add_argument(
        "--run-background",
        action="store_true",
        help="Detach the FastAPI service into the background and return the child PID.",
    )
    serve_parser.add_argument(
        "--background-log-file",
        default="",
        help="Optional log file path for --run-background.",
    )
    serve_parser.add_argument(
        "--background-pidfile",
        default="",
        help="Optional pidfile path for --run-background.",
    )
    parser._serve_parser = serve_parser

    config_menu_parser = subparsers.add_parser(
        "config-menu",
        help="Launch the interactive system.json configuration menu.",
    )
    config_menu_parser.add_argument(
        "--config",
        default="",
        help="Optional path to system.json configuration file.",
    )

    config_parser = subparsers.add_parser(
        "config",
        help="Non-interactive system.json configuration helpers.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Initialize system.json with CMTS defaults.",
    )
    config_init_parser.add_argument(
        "--path",
        default="",
        help="Optional target system.json path.",
    )
    config_init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing system.json.",
    )
    config_init_parser.add_argument(
        "--print",
        dest="print_output",
        action="store_true",
        help="Print the resulting JSON payload.",
    )
    config_init_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write; only print when --print is set.",
    )

    config_validate_parser = config_subparsers.add_parser(
        "validate",
        help="Validate system.json for CMTS readiness.",
    )
    config_validate_parser.add_argument(
        "--path",
        default="",
        help="Optional system.json path override.",
    )
    config_validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit validation output as JSON.",
    )

    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Print the effective system.json payload.",
    )
    config_show_parser.add_argument(
        "--path",
        default="",
        help="Optional system.json path override.",
    )
    config_show_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output.",
    )

    return parser


def _build_launcher(args: argparse.Namespace) -> CmtsOrchestratorLauncher:
    from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher

    config_value = args.config
    sg_id_value = args.sg_id
    owner_id_value = args.owner_id
    state_dir_value = args.state_dir
    election_name_value = args.election_name
    cmts_hostname_value = str(getattr(args, "cmts_hostname", "")).strip()
    read_community_value = str(getattr(args, "read_community", "")).strip()
    write_community_value = str(getattr(args, "write_community", "")).strip()

    mode_value = OrchestratorMode(args.mode)

    config_path: Path | None = Path(config_value) if config_value != "" else None
    state_dir: Path | None = Path(state_dir_value) if state_dir_value != "" else None
    sg_id: ServiceGroupId | None = None
    if sg_id_value != "":
        sg_id = CmtsOrchestratorLauncher._parse_sg_id(sg_id_value)
    owner_id: OwnerId | None = OwnerId(owner_id_value) if owner_id_value != "" else None
    election_name: CoordinationElectionName | None = None
    if election_name_value != "":
        election_name = CoordinationElectionName(election_name_value)

    snmp_port_value = _resolve_snmp_port_value(args, sys.argv[1:])
    if snmp_port_value is not None and int(snmp_port_value) <= 0:
        raise ValueError(f"snmp-port must be greater than zero (got {snmp_port_value}).")
    _validate_non_negative(args.target_service_groups, "target-service-groups")
    _validate_positive(args.tick_interval_seconds, "tick-interval-seconds")
    _validate_positive(args.leader_ttl_seconds, "leader-ttl-seconds")
    _validate_positive(args.lease_ttl_seconds, "lease-ttl-seconds")

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
        adapter_hostname=HostNameStr(cmts_hostname_value) if cmts_hostname_value != "" else None,
        adapter_read_community=SnmpReadCommunity(read_community_value) if read_community_value != "" else None,
        adapter_write_community=SnmpWriteCommunity(write_community_value) if write_community_value != "" else None,
        adapter_port=int(snmp_port_value) if snmp_port_value is not None else None,
    )


def _resolve_discovery_inputs(
    args: argparse.Namespace,
) -> tuple[HostNameStr, SnmpReadCommunity, SnmpWriteCommunity, int, Path]:
    from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings

    settings = CmtsOrchestratorSettings.from_system_config(
        config_path=Path(args.config) if args.config != "" else None
    )

    hostname = str(args.cmts_hostname).strip()
    if hostname == "":
        hostname = str(settings.adapter.hostname).strip()
    if hostname == "":
        raise ValueError("cmts-hostname is required for discovery.")

    read_community = str(args.read_community).strip()
    if read_community == "":
        read_community = str(settings.adapter.community).strip()
    if read_community == "":
        read_community = str(SnmpReadCommunity("public"))

    write_community = str(args.write_community).strip()
    if write_community == "":
        write_community = str(settings.adapter.write_community).strip()
    if write_community == "":
        write_community = read_community

    state_dir_value = str(args.state_dir).strip()
    if state_dir_value == "":
        state_dir = Path(settings.state_dir)
    else:
        state_dir = Path(state_dir_value)

    return (
        HostNameStr(hostname),
        SnmpReadCommunity(read_community),
        SnmpWriteCommunity(write_community),
        int(args.port),
        state_dir,
    )


def _render_discovery_text(result: InventoryDiscoveryResultModel) -> str:
    lines: list[str] = []
    lines.append(f"cmts_host={result.cmts_host}")
    for entry in result.per_sg:
        lines.append(f"sg_id={int(entry.sg_id)} cm_count={int(entry.cm_count)}")
        lines.extend(
            [f"  mac={cm.mac} ipv4={cm.ipv4} ipv6={cm.ipv6}" for cm in entry.cms]
        )
    return "\n".join(lines)


def _extract_flag_value(argv: list[str], flag: str) -> str | None:
    for idx, token in enumerate(argv):
        if token == flag:
            if idx + 1 < len(argv):
                return argv[idx + 1]
            return ""
        if token.startswith(f"{flag}="):
            return token[len(flag) + 1 :]
    return None


def _warn_deprecated_cmts_port() -> None:
    global _cmts_port_warned
    if _cmts_port_warned:
        return
    _cmts_port_warned = True
    print("DEPRECATED: --cmts-port is deprecated; use --snmp-port.", file=sys.stderr)


def _resolve_snmp_port_value(
    args: argparse.Namespace,
    argv: list[str],
) -> int | None:
    snmp_port_value = getattr(args, "snmp_port", None)
    cmts_value = _extract_flag_value(argv, _DEPRECATED_CMTS_PORT_FLAG)
    snmp_value = _extract_flag_value(argv, _SNMP_PORT_FLAG)
    if cmts_value is not None:
        _warn_deprecated_cmts_port()
    if snmp_value is not None:
        snmp_port_value = int(snmp_value)
    return snmp_port_value


def _validate_non_negative(value: int | None, name: str) -> None:
    if value is None:
        return
    if int(value) < 0:
        raise ValueError(f"{name} must be non-negative (got {value}).")


def _validate_positive(value: int | float | None, name: str) -> None:
    if value is None:
        return
    if float(value) <= 0:
        raise ValueError(f"{name} must be greater than zero (got {value}).")


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

    if args.command == "discover":
        from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService

        try:
            cmts_hostname, read_community, write_community, port, state_dir = _resolve_discovery_inputs(args)
            result = CmtsInventoryDiscoveryService.run_discovery(
                cmts_hostname=cmts_hostname,
                read_community=read_community,
                write_community=write_community,
                port=port,
                state_dir=state_dir,
            )
        except ValidationError as exc:
            _print_validation_errors(exc)
            return EXIT_CODE_USAGE
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return EXIT_CODE_USAGE
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return EXIT_CODE_FAILURE

        if args.text:
            print(_render_discovery_text(result))
        else:
            print(result.model_dump_json(indent=2))
        return SUCCESS_EXIT_CODE

    if args.command == "serve":
        from pypnm_cmts.combined_mode import COMBINED_MODE_ENV
        from pypnm_cmts.config.orchestrator_config import (
            ENV_ADAPTER_HOSTNAME,
            ENV_ADAPTER_READ_COMMUNITY,
            ENV_ADAPTER_WRITE_COMMUNITY,
            CmtsOrchestratorSettings,
        )

        run_background = bool(getattr(args, "run_background", False))
        background_log_file = str(getattr(args, "background_log_file", "")).strip()
        background_pidfile = str(getattr(args, "background_pidfile", "")).strip()

        if args.with_runner and args.reload:
            print(
                "ERROR: --with-runner cannot be used with --reload.",
                file=sys.stderr,
            )
            return EXIT_CODE_USAGE
        if run_background and args.reload:
            print(
                "ERROR: --run-background cannot be used with --reload.",
                file=sys.stderr,
            )
            return EXIT_CODE_USAGE
        if args.ssl:
            print(f"🔒 Launching FastAPI with HTTPS on https://{args.host}:{args.port}")
        else:
            print(f"🌐 Launching FastAPI with HTTP on http://{args.host}:{args.port}")

        _prepare_runtime_paths_for_serve(args)
        if run_background:
            return launch_background_serve(
                module_name="pypnm_cmts.cli",
                app_slug="pypnm-cmts",
                runtime_dir=CmtsSystemConfigSettings.runtime_dir(),
                argv=sys.argv[1:],
                log_file=background_log_file,
                pidfile=background_pidfile,
            )
        if args.limit_max_requests is not None and args.limit_max_requests < 0:
            print("[ERROR] --limit-max-requests must be >= 0")
            return EXIT_CODE_USAGE
        if str(args.cmts_hostname).strip() != "":
            os.environ[ENV_ADAPTER_HOSTNAME] = str(args.cmts_hostname).strip()
        if str(args.read_community).strip() != "":
            os.environ[ENV_ADAPTER_READ_COMMUNITY] = str(args.read_community).strip()
        if str(args.write_community).strip() != "":
            os.environ[ENV_ADAPTER_WRITE_COMMUNITY] = str(args.write_community).strip()
        if str(args.cm_snmpv2c_write_community).strip() != "":
            os.environ[ENV_CM_SNMPV2C_WRITE_COMMUNITY] = str(args.cm_snmpv2c_write_community).strip()
        if str(args.cm_tftp_ipv4).strip() != "":
            os.environ[ENV_CM_TFTP_IPV4] = str(args.cm_tftp_ipv4).strip()
        if str(args.cm_tftp_ipv6).strip() != "":
            os.environ[ENV_CM_TFTP_IPV6] = str(args.cm_tftp_ipv6).strip()
        if bool(args.mute_pypnm_endpoints):
            os.environ[ENV_MUTE_PYPNM_ENDPOINTS] = "1"
        if str(args.mute_tags).strip() != "":
            os.environ[ENV_MUTE_TAGS] = str(args.mute_tags).strip()
        if bool(args.mute_tags_hard):
            os.environ[ENV_MUTE_TAGS_HARD] = "1"

        try:
            settings = CmtsOrchestratorSettings.from_system_config()
        except ValidationError as exc:
            _print_validation_errors(exc)
            print(
                "See docs/faq/index.md for troubleshooting steps.",
                file=sys.stderr,
            )
            _print_serve_usage(parser)
            return EXIT_CODE_USAGE

        os.environ.setdefault("PYPNM_SERVE_ENV_FILE", str(default_profile_env_path()))
        resolved_workers, resolved_limit_max_requests = _resolve_runtime_worker_profile(args)
        sgw_enabled = _sgw_enabled(settings)

        uvicorn_args = {
            "app": "pypnm_cmts.api.main:app",
            "host": args.host,
            "port": args.port,
            "timeout_keep_alive": TIMEOUT_KEEP_ALIVE_SECONDS,
            "timeout_graceful_shutdown": TIMEOUT_GRACEFUL_SHUTDOWN_SECONDS,
            "log_level": args.log_level,
            "workers": resolved_workers,
            "access_log": not args.no_access_log,
        }
        if resolved_limit_max_requests > 0:
            uvicorn_args["limit_max_requests"] = resolved_limit_max_requests

        if sgw_enabled and resolved_workers != DEFAULT_WORKERS:
            print(
                "[WARN] SGW is enabled and uses per-process in-memory cache; forcing workers=1 to avoid duplicate SGW polling and incomplete SGW state across web workers."
            )
            uvicorn_args["workers"] = DEFAULT_WORKERS

        if args.reload:
            if resolved_workers != DEFAULT_WORKERS:
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

        if args.with_runner:
            os.environ[COMBINED_MODE_ENV] = "1"
            print("🔁 Combined mode runner enabled (controller + worker).")
            uvicorn_args["lifespan"] = "on"
            if resolved_workers != DEFAULT_WORKERS:
                print(
                    "[WARN] --workers is ignored when --with-runner is enabled; using workers=1 for combined mode."
                )
                uvicorn_args["workers"] = DEFAULT_WORKERS

        if args.ssl:
            uvicorn_args.update(
                {
                    "ssl_certfile": args.cert,
                    "ssl_keyfile": args.key,
                }
            )

        effective_workers = int(uvicorn_args["workers"])
        effective_limit_max_requests = int(uvicorn_args.get("limit_max_requests", 0))
        os.environ.setdefault("PYPNM_SERVE_SESSION_ID", f"{os.getpid()}-{int(time())}")
        os.environ["PYPNM_ACTIVE_WORKERS"] = str(effective_workers)
        os.environ["PYPNM_ACTIVE_LIMIT_MAX_REQUESTS"] = str(effective_limit_max_requests)
        _log_runtime_profile_selection(
            workers=effective_workers,
            limit_max_requests=effective_limit_max_requests,
        )
        launch_executable, launch_argv = _current_launch_command()
        launch_state_path = write_launch_state(
            build_launch_state(
                executable=launch_executable,
                argv=launch_argv,
            )
        )
        print(f"[INFO] Recorded serve launch state: {launch_state_path}")
        if args.reload:
            watcher_started, watcher_pidfile = ensure_reload_watcher(
                project_root=_project_root(),
                python_executable=sys.executable,
            )
            if watcher_started:
                print(f"[INFO] Started reload sentinel watcher: pidfile={watcher_pidfile}")
            else:
                print(f"[INFO] Reusing reload sentinel watcher: pidfile={watcher_pidfile}")
        _record_background_parent_pid()

        try:
            uvicorn.run(**uvicorn_args)
        except KeyboardInterrupt:
            return EXIT_CODE_SIGINT

        return SUCCESS_EXIT_CODE

    if args.command == "config-menu":
        from pypnm_cmts.tools.config_menu import CmtsConfigMenu

        config_path_value = str(args.config).strip()
        config_path: Path | None = None
        if config_path_value != "":
            config_path = Path(config_path_value)

        menu = CmtsConfigMenu(config_path=config_path)
        return menu.run()

    if args.command == "config":
        from pypnm_cmts.tools.config_commands import CmtsConfigCommands

        if args.config_command == "init":
            config_path = CmtsConfigCommands.resolve_config_path(args.path)
            return CmtsConfigCommands.init_config(
                path=config_path,
                force=bool(args.force),
                print_output=bool(args.print_output),
                dry_run=bool(args.dry_run),
            )
        if args.config_command == "validate":
            config_path = CmtsConfigCommands.resolve_config_path(args.path)
            return CmtsConfigCommands.validate_config(
                path=config_path,
                json_output=bool(args.json),
            )
        if args.config_command == "show":
            config_path = CmtsConfigCommands.resolve_config_path(args.path)
            return CmtsConfigCommands.show_config(
                path=config_path,
                pretty=bool(args.pretty),
            )
        print("ERROR: config subcommand is required.", file=sys.stderr)
        return EXIT_CODE_USAGE

    parser.print_help()
    return EXIT_CODE_USAGE


def _print_serve_usage(parser: argparse.ArgumentParser) -> None:
    serve_parser = getattr(parser, "_serve_parser", None)
    if serve_parser is not None:
        serve_parser.print_help()
    else:
        parser.print_help()


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

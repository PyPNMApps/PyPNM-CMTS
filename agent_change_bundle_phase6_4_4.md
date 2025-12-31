# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import contextlib
import signal
import threading
import time
from collections.abc import Callable
from pathlib import Path

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import CoordinationTickResultModel
from pypnm_cmts.lib.types import ServiceGroupId, TickIndex
from pypnm_cmts.orchestrator.pidfile_manager import PidFileRecord
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class CmtsOrchestratorRuntime:
    """
    Long-running orchestrator runtime that executes coordination ticks.
    """

    STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)

    def __init__(
        self,
        settings: CmtsOrchestratorSettings,
        manager: CoordinationManager,
        service_groups: list[ServiceGroupId],
        mode: OrchestratorMode,
        sg_id: ServiceGroupId | None,
    ) -> None:
        """
        Initialize the orchestrator runtime.

        Args:
            settings (CmtsOrchestratorSettings): Orchestrator settings instance.
            manager (CoordinationManager): Coordination manager dependency.
            service_groups (list[ServiceGroupId]): Service group inventory for ticks.
            mode (OrchestratorMode): Execution mode (standalone, controller, worker).
            sg_id (ServiceGroupId | None): Optional bound service group id for worker mode.
        """
        self._settings = settings
        self._manager = manager
        self._service_groups = service_groups
        self._mode = mode
        self._sg_id = sg_id
        self._stop_requested = False

    def stop(self) -> None:
        """
        Request that the runtime stop after the current tick.
        """
        self._stop_requested = True

    def run_forever(
        self,
        max_ticks: int | None = None,
        sleeper: Callable[[float], None] | None = None,
        on_tick: Callable[[CoordinationTickResultModel], None] | None = None,
        on_tick_indexed: Callable[[int, CoordinationTickResultModel], None] | None = None,
    ) -> list[CoordinationTickResultModel]:
        """
        Execute coordination ticks until stopped or max_ticks is reached.

        Args:
            max_ticks (int | None): Optional maximum number of ticks to execute.
            sleeper (Callable[[float], None] | None): Optional sleep function for tests.
            on_tick (Callable[[CoordinationTickResultModel], None] | None): Optional per-tick callback.
            on_tick_indexed (Callable[[int, CoordinationTickResultModel], None] | None): Optional per-tick callback with tick index.

        Returns:
            list[CoordinationTickResultModel]: Collected tick results when max_ticks is provided.
        """
        if max_ticks is not None and max_ticks < 0:
            raise ValueError("max_ticks must be non-negative.")

        pid_record = PidFileRecord.for_runtime(
            Path(self._settings.state_dir),
            self._mode,
            self._sg_id,
        )
        pid_ctx = pid_record if pid_record is not None else contextlib.nullcontext()

        if self._stop_requested:
            with pid_ctx, contextlib.suppress(Exception):
                self._manager.release_all()
            return []

        sleep_fn = sleeper if sleeper is not None else time.sleep
        tick_interval = float(self._settings.tick_interval_seconds)
        results: list[CoordinationTickResultModel] = []
        ticks = 0
        previous_handlers: dict[signal.Signals, object] = {}
        register_signals = threading.current_thread() is threading.main_thread()

        def _handle_stop(signum: int, frame: object | None) -> None:
            self.stop()

        with pid_ctx:
            if register_signals:
                for sig in self.STOP_SIGNALS:
                    previous_handlers[sig] = signal.getsignal(sig)
                    signal.signal(sig, _handle_stop)
            try:
                while not self._stop_requested:
                    if self._mode == OrchestratorMode.CONTROLLER:
                        tick_result = self._manager.tick_leader_only()
                    else:
                        tick_result = self._manager.tick(self._service_groups)
                    tick_result = tick_result.model_copy(update={"tick_index": TickIndex(ticks + 1)})
                    if max_ticks is not None:
                        results.append(tick_result)
                    if on_tick is not None:
                        on_tick(tick_result)
                    if on_tick_indexed is not None:
                        on_tick_indexed(ticks + 1, tick_result)

                    ticks += 1
                    if max_ticks is not None and ticks >= max_ticks:
                        break
                    if self._stop_requested:
                        break
                    sleep_fn(tick_interval)
            finally:
                if register_signals:
                    for sig, handler in previous_handlers.items():
                        signal.signal(sig, handler)
                with contextlib.suppress(Exception):
                    self._manager.release_all()

        return results

__all__ = [
    "CmtsOrchestratorRuntime",
]

FILE: src/pypnm_cmts/orchestrator/pidfile_manager.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class PidFileRecord:
    """
    Best-effort pidfile lifecycle manager for orchestrator processes.
    """

    PID_DIR_NAME = "pids"
    CONTROLLER_PIDFILE = "controller.pid"
    WORKER_PID_PREFIX = "worker_"
    WORKER_UNBOUND_PIDFILE = "worker_unbound.pid"

    def __init__(self, state_dir: Path, pidfile_name: str) -> None:
        """
        Initialize the pidfile record.

        Args:
            state_dir (Path): Coordination state directory.
            pidfile_name (str): Pidfile name to write under the pid directory.
        """
        self._pidfile_path = state_dir / self.PID_DIR_NAME / pidfile_name

    @classmethod
    def for_controller(cls, state_dir: Path) -> PidFileRecord:
        """
        Build the controller pidfile record.
        """
        return cls(state_dir, cls.CONTROLLER_PIDFILE)

    @classmethod
    def for_worker(cls, state_dir: Path, sg_id: ServiceGroupId) -> PidFileRecord:
        """
        Build the worker pidfile record for a bound service group.
        """
        return cls(state_dir, f"{cls.WORKER_PID_PREFIX}{int(sg_id)}.pid")

    @classmethod
    def for_worker_unbound(cls, state_dir: Path) -> PidFileRecord:
        """
        Build the pidfile record for an unbound worker.
        """
        return cls(state_dir, cls.WORKER_UNBOUND_PIDFILE)

    @classmethod
    def for_runtime(
        cls,
        state_dir: Path,
        mode: OrchestratorMode,
        sg_id: ServiceGroupId | None,
    ) -> PidFileRecord | None:
        """
        Build the pidfile record for the runtime mode.
        """
        if mode == OrchestratorMode.CONTROLLER:
            return cls.for_controller(state_dir)
        if mode == OrchestratorMode.WORKER:
            if sg_id is None:
                return cls.for_worker_unbound(state_dir)
            return cls.for_worker(state_dir, sg_id)
        if mode == OrchestratorMode.STANDALONE:
            return cls.for_controller(state_dir)
        return None

    def __enter__(self) -> PidFileRecord:
        """
        Write the pidfile best-effort.
        """
        self._write()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """
        Remove the pidfile best-effort.
        """
        self._cleanup()

    def _write(self) -> None:
        with contextlib.suppress(Exception):
            self._pidfile_path.parent.mkdir(parents=True, exist_ok=True)
            self._pidfile_path.write_text(f"{os.getpid()}\n", encoding="utf-8")

    def _cleanup(self) -> None:
        with contextlib.suppress(Exception):
            if self._pidfile_path.exists():
                self._pidfile_path.unlink()

    @property
    def pidfile_path(self) -> Path:
        """
        Return the pidfile path.
        """
        return self._pidfile_path


__all__ = [
    "PidFileRecord",
]

FILE: src/pypnm_cmts/cli.py
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
from pypnm.lib.types import HostNameStr, SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.orchestrator.models import OrchestratorRunResultModel
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__

SUCCESS_EXIT_CODE = 0
EXIT_CODE_USAGE = 2
EXIT_CODE_FAILURE = 1
HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 8000
LOG_LEVEL_DEFAULT = "info"
DEFAULT_WORKERS = 1
TIMEOUT_KEEP_ALIVE_SECONDS = 120
DEFAULT_SNMP_PORT = 161


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
        help="Execution mode: standalone, controller, worker, or combined.",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Optional path to system.json configuration file.",
    )
    parser.add_argument(
        "--cmts-hostname",
        default="",
        help="Optional CMTS hostname/IP override for auto-discovery (adapter.hostname).",
    )
    parser.add_argument(
        "--read-community",
        default="",
        help="Optional SNMPv2c read community override (adapter.community).",
    )
    parser.add_argument(
        "--write-community",
        default="",
        help="Optional SNMPv2c write community override (adapter.write_community).",
    )
    parser.add_argument(
        "--cmts-port",
        type=int,
        default=None,
        help="Optional SNMP port override for CMTS discovery (adapter.port).",
    )
    parser.add_argument(
        "--sg-id",
        default="",
        help="Optional service group identifier (bound worker mode).",
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


def _add_discover_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cmts-hostname",
        default="",
        help="CMTS hostname or IP address.",
    )
    parser.add_argument(
        "--read-community",
        default="",
        help="SNMPv2c read community string (default: public).",
    )
    parser.add_argument(
        "--write-community",
        default="",
        help="Optional SNMPv2c write community string (defaults to read community when empty).",
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
        help="Optional path to system.json configuration file.",
    )
    parser.add_argument(
        "--state-dir",
        default="",
        help="Optional coordination state directory override.",
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

    discover_parser = subparsers.add_parser("discover", help="Discover CMTS service groups and registered cable modems.")
    _add_discover_args(discover_parser)

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
        adapter_port=int(args.cmts_port) if getattr(args, "cmts_port", None) is not None else None,
    )


def _resolve_discovery_inputs(
    args: argparse.Namespace,
) -> tuple[HostNameStr, SnmpReadCommunity, SnmpWriteCommunity, int, Path]:
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

FILE: src/pypnm_cmts/orchestrator/launcher.py (substitute for runner.py/orchestrator.py)
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pypnm.lib.types import HostNameStr, SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.config.orchestrator_config import (
    CmtsOrchestratorSettings,
    ServiceGroupDescriptor,
)
from pypnm_cmts.config.owner_id_resolver import OwnerIdResolver
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import (
    CoordinationTickResultModel,
    ServiceGroupLeaseConflictModel,
)
from pypnm_cmts.coordination.service_group_lease import FileServiceGroupLease
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    LeaderId,
    OrchestratorRunId,
    OwnerId,
    ServiceGroupId,
    TickIndex,
)
from pypnm_cmts.orchestrator.models import (
    OrchestratorRunResultModel,
    OrchestratorStatusModel,
    ServiceGroupInventoryModel,
    WorkResultModel,
)
from pypnm_cmts.orchestrator.runtime import CmtsOrchestratorRuntime
from pypnm_cmts.orchestrator.sg_shard_planner import ServiceGroupShardPlanner
from pypnm_cmts.orchestrator.work_runner import WorkRunner
from pypnm_cmts.types.orchestrator_types import OrchestratorMode

DEFAULT_STATE_DIR = ".data/coordination"
DEFAULT_ELECTION_PREFIX = "cmts"
DEFAULT_ELECTION_LABEL = "primary"
INVENTORY_SOURCE_CONFIG = "config"
INVENTORY_SOURCE_DISCOVERY = "discovery"
INVENTORY_SOURCE_WORKER = "worker"
DEFAULT_CONFLICT_REASON = "Lease not acquired."


class CmtsOrchestratorLauncher:
    """
    One-shot orchestrator launcher for Phase-3 skeleton execution.
    """

    def __init__(
        self,
        config_path: CoordinationPath | None,
        mode: OrchestratorMode,
        sg_id: ServiceGroupId | None,
        owner_id: OwnerId | None = None,
        target_service_groups: int | None = None,
        shard_mode: str | None = None,
        tick_interval_seconds: float | None = None,
        leader_ttl_seconds: int | None = None,
        lease_ttl_seconds: int | None = None,
        state_dir: CoordinationPath | None = None,
        election_name: CoordinationElectionName | None = None,
        adapter_hostname: HostNameStr | None = None,
        adapter_read_community: SnmpReadCommunity | None = None,
        adapter_write_community: SnmpWriteCommunity | None = None,
        adapter_port: int | None = None,
        state_dir_override: Path | None = None,
    ) -> None:
        """
        Initialize a one-shot orchestrator launcher.

        Args:
            config_path (CoordinationPath | None): Optional system.json path override.
            mode (OrchestratorMode): Execution mode (standalone, controller, worker).
            sg_id (ServiceGroupId | None): Optional service group identifier for worker mode.
            owner_id (OwnerId | None): Optional explicit owner id override.
            target_service_groups (int | None): Optional target service group override.
            shard_mode (str | None): Optional shard mode override.
            tick_interval_seconds (float | None): Optional tick interval override.
            leader_ttl_seconds (int | None): Optional leader TTL override.
            lease_ttl_seconds (int | None): Optional lease TTL override.
            state_dir (CoordinationPath | None): Optional coordination state directory override.
            election_name (CoordinationElectionName | None): Optional election name override.
            adapter_hostname (HostNameStr | None): Optional CMTS hostname override.
            adapter_read_community (SnmpReadCommunity | None): Optional SNMP read community override.
            adapter_write_community (SnmpWriteCommunity | None): Optional SNMP write community override.
            adapter_port (int | None): Optional SNMP port override.
            state_dir_override (Path | None): Optional state directory override (tests only).
        """
        self._config_path = config_path
        self._mode = mode
        self._sg_id = sg_id
        self._owner_id = owner_id
        self._target_service_groups = target_service_groups
        self._shard_mode = shard_mode
        self._tick_interval_seconds = tick_interval_seconds
        self._leader_ttl_seconds = leader_ttl_seconds
        self._lease_ttl_seconds = lease_ttl_seconds
        self._state_dir = state_dir
        self._election_name = election_name
        self._adapter_hostname = adapter_hostname
        self._adapter_read_community = adapter_read_community
        self._adapter_write_community = adapter_write_community
        self._adapter_port = adapter_port
        self._state_dir_override = state_dir_override

    def run_once(self) -> OrchestratorRunResultModel:
        """
        Execute a single orchestration tick and return a structured result.

        Returns:
            OrchestratorRunResultModel: Structured result for one orchestration tick.
        """
        settings = CmtsOrchestratorSettings.from_system_config(
            config_path=self._config_path if self._config_path != "" else None
        )
        settings = self._apply_overrides(settings)

        state_dir = self._resolve_state_dir()
        owner_id = OwnerIdResolver.resolve(str(settings.owner_id), state_dir)
        leader_id = self._build_leader_id(owner_id)
        election_name = self._build_election_name(settings)

        if self._mode == OrchestratorMode.CONTROLLER:
            service_groups, source = self._build_controller_service_groups(
                settings=settings,
                state_dir=state_dir,
                is_leader=False,
            )
        else:
            service_groups, source = self._build_service_groups(settings, state_dir)
        inventory = ServiceGroupInventoryModel(
            sg_ids=service_groups,
            count=len(service_groups),
            source=source,
        )

        desired_sg_ids = list(service_groups)
        worker_count = 0
        if self._mode == OrchestratorMode.CONTROLLER:
            desired_sg_ids, worker_count = self._plan_controller_service_groups(
                settings=settings,
                service_groups=service_groups,
            )

        effective_target = self._effective_target_service_groups(
            settings=settings,
            inventory_count=len(service_groups),
        )
        if self._mode == OrchestratorMode.CONTROLLER and int(settings.target_service_groups) == 0:
            effective_target = len(desired_sg_ids)

        manager = CoordinationManager(
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=OwnerId(str(owner_id)),
            leader_ttl_seconds=int(settings.leader_ttl_seconds),
            lease_ttl_seconds=int(settings.lease_ttl_seconds),
            target_service_groups=effective_target,
            shard_mode=settings.shard_mode,
            leader_enabled=self._mode == OrchestratorMode.CONTROLLER,
            leader_id_validator=self._leader_id_validator() if self._mode == OrchestratorMode.CONTROLLER else None,
        )

        if self._mode == OrchestratorMode.CONTROLLER:
            tick_result = manager.tick_leader_only()
            leader_status = manager.leader_status()
            service_groups, source = self._build_controller_service_groups(
                settings=settings,
                state_dir=state_dir,
                is_leader=leader_status.is_leader,
            )
            inventory = ServiceGroupInventoryModel(
                sg_ids=service_groups,
                count=len(service_groups),
                source=source,
            )
            desired_sg_ids, worker_count = self._plan_controller_service_groups(
                settings=settings,
                service_groups=service_groups,
            )
            effective_target = self._effective_target_service_groups(
                settings=settings,
                inventory_count=len(service_groups),
            )
            if int(settings.target_service_groups) == 0:
                effective_target = len(desired_sg_ids)
        else:
            tick_target = service_groups
            tick_result = manager.tick(tick_target)
        tick_value = int(tick_result.tick_index)
        tick_index = TickIndex(tick_value if tick_value > 0 else 1)
        acquired_sg_ids = sorted(tick_result.acquired_sg_ids, key=int)
        coordination_status = manager.status()
        if self._mode == OrchestratorMode.CONTROLLER:
            held_sg_ids = []
        else:
            held_sg_ids = sorted(coordination_status.held_sg_ids, key=int)
        conflicts = self._build_conflicts(
            desired_sg_ids=desired_sg_ids,
            leased_sg_ids=held_sg_ids,
            state_dir=state_dir,
            election_name=election_name,
            owner_id=OwnerId(str(owner_id)),
            lease_ttl_seconds=int(settings.lease_ttl_seconds),
        )
        tick_result = tick_result.model_copy(
            update={
                "enabled_sg_ids": sorted(service_groups, key=int),
                "desired_sg_ids": sorted(desired_sg_ids, key=int),
                "leased_sg_ids": sorted(held_sg_ids, key=int),
                "conflicts": conflicts,
                "worker_count": worker_count,
            }
        )
        work_sg_ids = self._select_work_sg_ids(
            acquired_sg_ids=acquired_sg_ids,
            held_sg_ids=held_sg_ids,
        )
        lease_held = self._is_worker_lease_held(held_sg_ids=held_sg_ids)
        run_id = self._build_run_id(acquired_sg_ids=work_sg_ids, tick_index=tick_index, lease_held=lease_held)
        work_results = self._run_worker_tests(
            settings=settings,
            state_dir=state_dir,
            tick_index=tick_index,
            acquired_sg_ids=work_sg_ids,
            lease_held=lease_held,
        )

        return OrchestratorRunResultModel(
            mode=self._mode,
            tick_index=tick_index,
            run_id=run_id,
            lease_held=lease_held,
            inventory=inventory,
            coordination_tick=tick_result,
            coordination_status=coordination_status,
            leader_status=manager.leader_status(),
            target_service_groups=effective_target,
            work_results=work_results,
        )

    def run_forever(
        self,
        on_tick: Callable[[OrchestratorRunResultModel], None] | None = None,
        max_ticks: int | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> list[CoordinationTickResultModel]:
        """
        Execute the orchestration runtime tick loop until stopped.

        Args:
            on_tick (Callable[[OrchestratorRunResultModel], None] | None): Optional per-tick callback.
            max_ticks (int | None): Optional maximum ticks to execute (tests only).
            sleeper (Callable[[float], None] | None): Optional sleep override (tests only).

        Returns:
            list[CoordinationTickResultModel]: Collected tick results when max_ticks is provided.
        """
        settings = CmtsOrchestratorSettings.from_system_config(
            config_path=self._config_path if self._config_path != "" else None
        )
        settings = self._apply_overrides(settings)

        state_dir = self._resolve_state_dir()
        owner_id = OwnerIdResolver.resolve(str(settings.owner_id), state_dir)
        leader_id = self._build_leader_id(owner_id)
        election_name = self._build_election_name(settings)

        service_groups, source = self._build_service_groups(settings, state_dir)
        inventory = ServiceGroupInventoryModel(
            sg_ids=service_groups,
            count=len(service_groups),
            source=source,
        )
        desired_sg_ids = list(service_groups)
        worker_count = 0
        if self._mode == OrchestratorMode.CONTROLLER:
            desired_sg_ids, worker_count = self._plan_controller_service_groups(
                settings=settings,
                service_groups=service_groups,
            )
        effective_target = self._effective_target_service_groups(
            settings=settings,
            inventory_count=len(service_groups),
        )
        if self._mode == OrchestratorMode.CONTROLLER and int(settings.target_service_groups) == 0:
            effective_target = len(desired_sg_ids)

        manager = CoordinationManager(
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=OwnerId(str(owner_id)),
            leader_ttl_seconds=int(settings.leader_ttl_seconds),
            lease_ttl_seconds=int(settings.lease_ttl_seconds),
            target_service_groups=effective_target,
            shard_mode=settings.shard_mode,
            leader_enabled=self._mode == OrchestratorMode.CONTROLLER,
            leader_id_validator=self._leader_id_validator() if self._mode == OrchestratorMode.CONTROLLER else None,
        )

        runtime = CmtsOrchestratorRuntime(
            settings=settings,
            manager=manager,
            service_groups=service_groups,
            mode=self._mode,
            sg_id=self._sg_id,
        )
        controller_inventory_source = source
        controller_inventory_initialized = False

        def _emit_result(tick_index: int, tick_result: CoordinationTickResultModel) -> None:
            if on_tick is None:
                return
            nonlocal service_groups, inventory, desired_sg_ids, worker_count, effective_target, controller_inventory_source, controller_inventory_initialized
            tick_value = TickIndex(int(tick_index))
            acquired_sg_ids = sorted(tick_result.acquired_sg_ids, key=int)
            coordination_status = manager.status()
            if self._mode == OrchestratorMode.CONTROLLER:
                held_sg_ids = []
                if coordination_status.is_leader and not controller_inventory_initialized:
                    service_groups, controller_inventory_source = self._build_controller_service_groups(
                        settings=settings,
                        state_dir=state_dir,
                        is_leader=True,
                    )
                    inventory = ServiceGroupInventoryModel(
                        sg_ids=service_groups,
                        count=len(service_groups),
                        source=controller_inventory_source,
                    )
                    desired_sg_ids, worker_count = self._plan_controller_service_groups(
                        settings=settings,
                        service_groups=service_groups,
                    )
                    effective_target = self._effective_target_service_groups(
                        settings=settings,
                        inventory_count=len(service_groups),
                    )
                    if int(settings.target_service_groups) == 0:
                        effective_target = len(desired_sg_ids)
                    controller_inventory_initialized = True
            else:
                held_sg_ids = sorted(coordination_status.held_sg_ids, key=int)
            conflicts = self._build_conflicts(
                desired_sg_ids=desired_sg_ids,
                leased_sg_ids=held_sg_ids,
                state_dir=state_dir,
                election_name=election_name,
                owner_id=OwnerId(str(owner_id)),
                lease_ttl_seconds=int(settings.lease_ttl_seconds),
            )
            tick_result = tick_result.model_copy(
                update={
                    "enabled_sg_ids": sorted(service_groups, key=int),
                    "desired_sg_ids": sorted(desired_sg_ids, key=int),
                    "leased_sg_ids": sorted(held_sg_ids, key=int),
                    "conflicts": conflicts,
                    "worker_count": worker_count,
                }
            )
            work_sg_ids = self._select_work_sg_ids(
                acquired_sg_ids=acquired_sg_ids,
                held_sg_ids=held_sg_ids,
            )
            lease_held = self._is_worker_lease_held(held_sg_ids=held_sg_ids)
            run_id = self._build_run_id(acquired_sg_ids=work_sg_ids, tick_index=tick_value, lease_held=lease_held)
            work_results = self._run_worker_tests(
                settings=settings,
                state_dir=state_dir,
                tick_index=tick_value,
                acquired_sg_ids=work_sg_ids,
                lease_held=lease_held,
            )
            result = OrchestratorRunResultModel(
                mode=self._mode,
                tick_index=tick_value,
                run_id=run_id,
                lease_held=lease_held,
                inventory=inventory,
                coordination_tick=tick_result,
                coordination_status=coordination_status,
                leader_status=manager.leader_status(),
                target_service_groups=effective_target,
                work_results=work_results,
            )
            on_tick(result)

        return runtime.run_forever(
            max_ticks=max_ticks,
            sleeper=sleeper,
            on_tick_indexed=_emit_result,
        )

    def build_status_snapshot(self) -> OrchestratorStatusModel:
        """
        Build an orchestration status snapshot without executing a tick.

        Returns:
            OrchestratorStatusModel: Status snapshot including inventory and coordination status.
        """
        settings = CmtsOrchestratorSettings.from_system_config(
            config_path=self._config_path if self._config_path != "" else None
        )
        settings = self._apply_overrides(settings)

        state_dir = self._resolve_state_dir()
        owner_id = OwnerIdResolver.resolve(str(settings.owner_id), state_dir)
        leader_id = self._build_leader_id(owner_id)
        election_name = self._build_election_name(settings)

        service_groups, source = self._build_service_groups(settings, state_dir)
        inventory = ServiceGroupInventoryModel(
            sg_ids=service_groups,
            count=len(service_groups),
            source=source,
        )
        effective_target = self._effective_target_service_groups(
            settings=settings,
            inventory_count=len(service_groups),
        )

        manager = CoordinationManager(
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=OwnerId(str(owner_id)),
            leader_ttl_seconds=int(settings.leader_ttl_seconds),
            lease_ttl_seconds=int(settings.lease_ttl_seconds),
            target_service_groups=effective_target,
            shard_mode=settings.shard_mode,
            leader_enabled=self._mode == OrchestratorMode.CONTROLLER,
            leader_id_validator=self._leader_id_validator() if self._mode == OrchestratorMode.CONTROLLER else None,
        )

        return OrchestratorStatusModel(
            mode=self._mode,
            inventory=inventory,
            coordination_status=manager.status(),
            leader_status=manager.leader_status(),
            target_service_groups=effective_target,
        )

    def _resolve_state_dir(self) -> Path:
        if self._state_dir_override is not None:
            state_dir = self._state_dir_override
        elif self._state_dir is not None and str(self._state_dir).strip() != "":
            state_dir = Path(self._state_dir)
        else:
            state_dir = Path(DEFAULT_STATE_DIR)
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def _build_election_name(self, settings: CmtsOrchestratorSettings) -> CoordinationElectionName:
        if str(settings.election_name).strip() != "":
            return CoordinationElectionName(str(settings.election_name).strip())
        label = settings.adapter.label.strip() if settings.adapter.label.strip() != "" else DEFAULT_ELECTION_LABEL
        value = f"{DEFAULT_ELECTION_PREFIX}-{label}"
        return CoordinationElectionName(value)

    def _build_leader_id(self, owner_id: OwnerId) -> LeaderId:
        owner_value = str(owner_id).strip()
        if owner_value == "":
            owner_value = str(owner_id)
        if self._mode == OrchestratorMode.CONTROLLER:
            if owner_value.startswith("controller-"):
                return LeaderId(owner_value)
            if owner_value.startswith("worker-"):
                stripped = owner_value[len("worker-") :]
                if stripped == "":
                    stripped = str(owner_id).strip()
                return LeaderId(f"controller-{stripped}")
            return LeaderId(f"controller-{owner_value}")
        if owner_value.startswith("worker-"):
            return LeaderId(owner_value)
        if owner_value.startswith("controller-"):
            stripped = owner_value[len("controller-") :]
            if stripped == "":
                stripped = str(owner_id).strip()
            return LeaderId(f"worker-{stripped}")
        return LeaderId(f"worker-{owner_value}")

    @staticmethod
    def _leader_id_validator() -> Callable[[LeaderId], bool]:
        def _is_controller(leader_id: LeaderId) -> bool:
            value = str(leader_id).strip()
            return value != "" and not value.startswith("worker-")

        return _is_controller

    def _build_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        if self._mode == OrchestratorMode.WORKER:
            return self._build_worker_service_groups(settings, state_dir)
        return self._build_inventory_service_groups(settings, state_dir)

    def _build_worker_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        if self._sg_id is None:
            snapshot = self._load_inventory_snapshot(state_dir)
            if snapshot is not None:
                return (sorted(snapshot.discovered_sg_ids, key=int), INVENTORY_SOURCE_DISCOVERY)
            if settings.service_groups:
                return self._build_config_service_groups(settings)
            if self._should_discover(settings):
                raise ValueError("inventory snapshot not found for worker mode.")
            return ([], INVENTORY_SOURCE_WORKER)

        config_groups = self._build_config_service_groups(settings)[0]
        if settings.service_groups:
            if self._sg_id not in config_groups:
                raise ValueError("worker sg-id is not enabled in configuration.")
            return ([self._sg_id], INVENTORY_SOURCE_CONFIG)

        return ([self._sg_id], INVENTORY_SOURCE_WORKER)

    def _build_inventory_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        if bool(settings.auto_discover) or not settings.service_groups:
            return self._build_discovered_service_groups(settings, state_dir)
        return self._build_config_service_groups(settings)

    def _build_controller_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        is_leader: bool,
    ) -> tuple[list[ServiceGroupId], str]:
        if is_leader and self._should_discover(settings):
            return self._build_discovered_service_groups(settings, state_dir)

        snapshot = self._load_inventory_snapshot(state_dir)
        if snapshot is not None:
            return (sorted(snapshot.discovered_sg_ids, key=int), INVENTORY_SOURCE_DISCOVERY)

        service_groups, source = self._build_config_service_groups(settings)
        if is_leader and service_groups:
            self._persist_inventory_snapshot(settings, state_dir, service_groups)
        return (service_groups, source)

    def _build_discovered_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        result = CmtsInventoryDiscoveryService.run_discovery(
            cmts_hostname=settings.adapter.hostname,
            read_community=settings.adapter.community,
            write_community=settings.adapter.write_community,
            port=int(settings.adapter.port),
            state_dir=state_dir,
        )
        return (sorted(result.discovered_sg_ids, key=int), INVENTORY_SOURCE_DISCOVERY)

    def _load_inventory_snapshot(self, state_dir: Path) -> InventoryDiscoveryResultModel | None:
        snapshot_path = state_dir / "inventory" / "discovery.json"
        if not snapshot_path.exists():
            return None
        try:
            content = snapshot_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise ValueError("inventory snapshot could not be read.") from exc
        try:
            return InventoryDiscoveryResultModel.model_validate_json(content)
        except Exception as exc:
            raise ValueError("inventory snapshot is invalid.") from exc

    def _persist_inventory_snapshot(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        sg_ids: list[ServiceGroupId],
    ) -> None:
        snapshot = InventoryDiscoveryResultModel(
            cmts_host=HostNameStr(str(settings.adapter.hostname)),
            discovered_sg_ids=sorted(sg_ids, key=int),
            per_sg=[],
        )
        inventory_dir = state_dir / "inventory"
        inventory_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = inventory_dir / "discovery.json"
        snapshot_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

    def _build_config_service_groups(self, settings: CmtsOrchestratorSettings) -> tuple[list[ServiceGroupId], str]:
        enabled_ids: list[ServiceGroupId] = []
        for entry in settings.service_groups:
            if not entry.enabled:
                continue
            enabled_ids.append(entry.sg_id)
        return (sorted(enabled_ids, key=int), INVENTORY_SOURCE_CONFIG)

    def _plan_controller_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        service_groups: list[ServiceGroupId],
    ) -> tuple[list[ServiceGroupId], int]:
        descriptors = self._build_planner_descriptors(settings, service_groups)
        return ServiceGroupShardPlanner.plan(
            descriptors=descriptors,
            shard_mode=settings.shard_mode,
            target_service_groups=int(settings.target_service_groups),
            worker_cap=int(settings.worker_cap),
        )

    def _build_planner_descriptors(
        self,
        settings: CmtsOrchestratorSettings,
        service_groups: list[ServiceGroupId],
    ) -> list[ServiceGroupDescriptor]:
        if settings.service_groups:
            return list(settings.service_groups)
        return [ServiceGroupDescriptor(sg_id=sg_id) for sg_id in service_groups]

    def _effective_target_service_groups(self, settings: CmtsOrchestratorSettings, inventory_count: int) -> int:
        if self._mode == OrchestratorMode.WORKER and self._sg_id is not None:
            requested = 1
        else:
            requested = int(settings.target_service_groups)
        if inventory_count <= 0:
            return 0
        return min(requested, inventory_count)

    def _run_worker_tests(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        tick_index: TickIndex,
        acquired_sg_ids: list[ServiceGroupId],
        lease_held: bool,
    ) -> list[WorkResultModel]:
        if self._mode != OrchestratorMode.WORKER:
            return []
        if not lease_held:
            return []
        if not acquired_sg_ids:
            return []

        tests = [str(test_name) for test_name in settings.default_tests]
        runner = WorkRunner(state_dir=state_dir)
        sg_id = sorted(acquired_sg_ids, key=int)[0]
        run_id = self._build_run_id_for_sg(sg_id=sg_id, tick_index=tick_index)
        return runner.run_tests(sg_id=sg_id, tests=tests, run_id=run_id)

    def _build_run_id(
        self,
        acquired_sg_ids: list[ServiceGroupId],
        tick_index: TickIndex,
        lease_held: bool,
    ) -> OrchestratorRunId:
        if self._mode != OrchestratorMode.WORKER:
            return OrchestratorRunId("")
        if not lease_held:
            return OrchestratorRunId("")
        if not acquired_sg_ids:
            return OrchestratorRunId("")
        sg_id = sorted(acquired_sg_ids, key=int)[0]
        return self._build_run_id_for_sg(sg_id=sg_id, tick_index=tick_index)

    def _build_run_id_for_sg(
        self,
        sg_id: ServiceGroupId,
        tick_index: TickIndex,
    ) -> OrchestratorRunId:
        value = f"sg{int(sg_id)}_tick{int(tick_index):06d}"
        return OrchestratorRunId(value)

    def _build_conflicts(
        self,
        desired_sg_ids: list[ServiceGroupId],
        leased_sg_ids: list[ServiceGroupId],
        state_dir: Path,
        election_name: CoordinationElectionName,
        owner_id: OwnerId,
        lease_ttl_seconds: int,
    ) -> list[ServiceGroupLeaseConflictModel]:
        if not desired_sg_ids:
            return []

        conflicts: list[ServiceGroupLeaseConflictModel] = []
        for sg_id in sorted(desired_sg_ids, key=int):
            if sg_id in leased_sg_ids:
                continue
            lease = FileServiceGroupLease(
                state_dir=state_dir,
                election_name=election_name,
                sg_id=sg_id,
                owner_id=owner_id,
                ttl_seconds=int(lease_ttl_seconds),
            )
            status = lease.status()
            reason = status.message if status.message != "" else DEFAULT_CONFLICT_REASON
            conflicts.append(
                ServiceGroupLeaseConflictModel(
                    sg_id=sg_id,
                    owner_id=status.owner_id,
                    reason=reason,
                )
            )
        return conflicts

    def _select_work_sg_ids(
        self,
        acquired_sg_ids: list[ServiceGroupId],
        held_sg_ids: list[ServiceGroupId],
    ) -> list[ServiceGroupId]:
        if acquired_sg_ids:
            return sorted(acquired_sg_ids, key=int)[:1]
        return sorted(held_sg_ids, key=int)[:1]

    def _is_worker_lease_held(self, held_sg_ids: list[ServiceGroupId]) -> bool:
        if self._mode != OrchestratorMode.WORKER:
            return False
        return bool(held_sg_ids)

    def _should_discover(self, settings: CmtsOrchestratorSettings) -> bool:
        return bool(settings.auto_discover) or not settings.service_groups

    def _apply_overrides(self, settings: CmtsOrchestratorSettings) -> CmtsOrchestratorSettings:
        data = settings.model_dump()
        adapter_data = dict(data.get("adapter", {}))

        if self._owner_id is not None and str(self._owner_id).strip() != "":
            data["owner_id"] = self._owner_id
        if self._target_service_groups is not None:
            data["target_service_groups"] = int(self._target_service_groups)
        if self._shard_mode is not None and self._shard_mode.strip() != "":
            data["shard_mode"] = self._shard_mode
        if self._tick_interval_seconds is not None:
            data["tick_interval_seconds"] = float(self._tick_interval_seconds)
        if self._leader_ttl_seconds is not None:
            data["leader_ttl_seconds"] = int(self._leader_ttl_seconds)
        if self._lease_ttl_seconds is not None:
            data["lease_ttl_seconds"] = int(self._lease_ttl_seconds)
        if self._state_dir is not None and str(self._state_dir).strip() != "":
            data["state_dir"] = str(self._state_dir)
        if self._election_name is not None:
            data["election_name"] = self._election_name
        if self._adapter_hostname is not None and str(self._adapter_hostname).strip() != "":
            adapter_data["hostname"] = str(self._adapter_hostname)
        if self._adapter_read_community is not None and str(self._adapter_read_community).strip() != "":
            adapter_data["community"] = str(self._adapter_read_community)
        if self._adapter_write_community is not None:
            adapter_data["write_community"] = str(self._adapter_write_community)
        if self._adapter_port is not None:
            adapter_data["port"] = int(self._adapter_port)

        data["adapter"] = adapter_data

        return CmtsOrchestratorSettings.model_validate(data)

    @staticmethod
    def _parse_sg_id(value: str) -> ServiceGroupId:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("service group id must be non-empty.")
        try:
            return ServiceGroupId(int(trimmed))
        except ValueError as exc:
            raise ValueError("service group id must be a numeric value.") from exc


__all__ = [
    "CmtsOrchestratorLauncher",
    "DEFAULT_STATE_DIR",
]

FILE: src/pypnm_cmts/api/routes/operational/router.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import APIRouter
from starlette.responses import JSONResponse

from pypnm_cmts.api.routes.operational.schemas import (
    HealthResponseModel,
    OperationalStatusResponseModel,
    ReadyResponseModel,
    VersionResponseModel,
)
from pypnm_cmts.api.routes.operational.service import OperationalService
from pypnm_cmts.lib.constants import OperationalStatus


class OperationalRouter:
    """
    FastAPI router for operational endpoints.
    """

    def __init__(
        self,
        prefix: str = "/ops",
        tags: list[str] | None = None,
    ) -> None:
        if tags is None:
            tags = ["Operational"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._service = OperationalService()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/health",
            response_model=HealthResponseModel,
            summary="Operational health probe",
            description="Returns a basic liveness signal and runtime metadata.",
        )
        def health() -> HealthResponseModel:
            """
            **Operational Health**

            Returns liveness status and runtime identity metadata.
            """
            return self._service.health()

        @self.router.get(
            "/ready",
            response_model=ReadyResponseModel,
            summary="Operational readiness probe",
            description="Returns readiness based on local prerequisites.",
            responses={
                HTTPStatus.SERVICE_UNAVAILABLE.value: {
                    "model": ReadyResponseModel,
                    "description": "Not ready",
                }
            },
        )
        def ready() -> ReadyResponseModel:
            """
            **Operational Readiness**

            Validates local prerequisites for orchestration readiness.
            """
            ready_payload = self._service.ready()
            if ready_payload.status != OperationalStatus.OK:
                return JSONResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    content=ready_payload.model_dump(mode="json"),
                )
            return ready_payload

        @self.router.get(
            "/version",
            response_model=VersionResponseModel,
            summary="Operational version probe",
            description="Returns version and runtime metadata.",
        )
        def version() -> VersionResponseModel:
            """
            **Operational Version**

            Returns package and runtime version metadata.
            """
            return self._service.version()

        @self.router.get(
            "/status",
            response_model=OperationalStatusResponseModel,
            summary="Operational process status",
            description="Returns process and coordination snapshot metadata.",
        )
        def status() -> OperationalStatusResponseModel:
            """
            **Operational Status**

            Returns process status and coordination metadata.
            """
            return self._service.status()

router = OperationalRouter().router

__all__ = [
    "router",
]

FILE: src/pypnm_cmts/api/routes/operational/service.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import contextlib
import logging
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypnm_cmts.api.routes.operational.schemas import (
    HealthResponseModel,
    OperationalIdentityModel,
    OperationalProcessInfoModel,
    OperationalStatusResponseModel,
    ReadyResponseModel,
    VersionResponseModel,
)
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import CoordinationElectionName, ServiceGroupId
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__


class OperationalService:
    """
    Operational endpoint service layer.
    """

    READY_PROBE_DIR_NAME = ".ready_check"
    READY_PROBE_FILE_PREFIX = "ready.check"
    READY_SUBDIRS = ("pids", "logs", "inventory")
    PID_DIR_NAME = "pids"
    CONTROLLER_PID_NAME = "controller.pid"
    WORKER_PID_PREFIX = "worker_"
    PID_SUFFIX = ".pid"
    UNBOUND_WORKER_NAME = "worker_unbound"

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def build_identity(self) -> OperationalIdentityModel:
        """
        Build runtime identity metadata for operational responses.
        """
        settings = CmtsOrchestratorSettings.from_system_config()
        return OperationalIdentityModel(
            mode=settings.mode,
            election_name=settings.election_name,
            state_dir=settings.state_dir,
            sg_id=self._select_worker_sg(settings),
        )

    def health(self) -> HealthResponseModel:
        """
        Build the operational health response.
        """
        meta = self.build_identity()
        return HealthResponseModel(
            status=OperationalStatus.OK,
            timestamp=self._utc_now(),
            meta=meta,
        )

    def ready(self) -> ReadyResponseModel:
        """
        Build the operational readiness response.
        """
        meta = self.build_identity()
        if meta.state_dir is None:
            return ReadyResponseModel(
                status=OperationalStatus.ERROR,
                timestamp=self._utc_now(),
                meta=meta,
                failed_check=ReadinessCheck.STATE_DIR,
                message="state_dir is not configured",
            )
        state_dir = Path(meta.state_dir)

        if meta.mode in (
            OrchestratorMode.CONTROLLER,
            OrchestratorMode.STANDALONE,
            OrchestratorMode.COMBINED,
        ):
            if not self._ensure_state_dir_exists(state_dir):
                return ReadyResponseModel(
                    status=OperationalStatus.ERROR,
                    timestamp=self._utc_now(),
                    meta=meta,
                    failed_check=ReadinessCheck.STATE_DIR_CREATE,
                    message=f"state_dir could not be created: {state_dir}",
                )
            if not self._ensure_state_subdirs(state_dir):
                return ReadyResponseModel(
                    status=OperationalStatus.ERROR,
                    timestamp=self._utc_now(),
                    meta=meta,
                    failed_check=ReadinessCheck.STATE_DIR_ACCESS,
                    message=f"state_dir subdirectories could not be created: {state_dir}",
                )
            if not self._ensure_state_dir_writable(state_dir):
                return ReadyResponseModel(
                    status=OperationalStatus.ERROR,
                    timestamp=self._utc_now(),
                    meta=meta,
                    failed_check=ReadinessCheck.STATE_DIR_ACCESS,
                    message=f"state_dir is not writable: {state_dir}",
                )

        if meta.mode == OrchestratorMode.WORKER:
            if not state_dir.exists():
                return ReadyResponseModel(
                    status=OperationalStatus.ERROR,
                    timestamp=self._utc_now(),
                    meta=meta,
                    failed_check=ReadinessCheck.STATE_DIR,
                    message=f"state_dir does not exist: {state_dir}",
                )
            if not self._ensure_state_dir_readable(state_dir):
                return ReadyResponseModel(
                    status=OperationalStatus.ERROR,
                    timestamp=self._utc_now(),
                    meta=meta,
                    failed_check=ReadinessCheck.STATE_DIR_READ,
                    message=f"state_dir is not readable: {state_dir}",
                )
            if meta.sg_id is None:
                return ReadyResponseModel(
                    status=OperationalStatus.ERROR,
                    timestamp=self._utc_now(),
                    meta=meta,
                    failed_check=ReadinessCheck.WORKER_SG,
                    message="worker mode requires sg_id to be set",
                )

        return ReadyResponseModel(
            status=OperationalStatus.OK,
            timestamp=self._utc_now(),
            meta=meta,
            failed_check=None,
            message="",
        )

    def version(self) -> VersionResponseModel:
        """
        Build the operational version response.
        """
        meta = self.build_identity()
        return VersionResponseModel(
            application="pypnm-cmts",
            version=__version__,
            python_version=sys.version.split()[0],
            build_metadata="",
            timestamp=self._utc_now(),
            meta=meta,
        )

    def status(self) -> OperationalStatusResponseModel:
        """
        Build the operational status response.
        """
        meta = self.build_identity()
        if meta.state_dir is None:
            return OperationalStatusResponseModel(
                status=OperationalStatus.ERROR,
                timestamp=self._utc_now(),
                meta=meta,
                controller=OperationalProcessInfoModel(),
                workers=[],
                pid_records_missing=True,
                pid_records_stale=False,
                fallback_used=False,
            )

        state_dir = Path(meta.state_dir)
        controller, workers, pid_records_missing, pid_records_stale = self._collect_pidfile_status(
            state_dir
        )

        fallback_used = False
        if pid_records_missing or pid_records_stale:
            fallback_used, controller, workers = self._apply_fallback_process_scan(
                meta.election_name, controller, workers
            )

        workers_sorted = sorted(
            workers,
            key=lambda entry: (
                entry.sg_id is None,
                entry.sg_id if entry.sg_id is not None else 0,
                entry.pid if entry.pid is not None else 0,
                str(entry.pidfile_path) if entry.pidfile_path is not None else "",
            ),
        )

        status_value = OperationalStatus.OK
        return OperationalStatusResponseModel(
            status=status_value,
            timestamp=self._utc_now(),
            meta=meta,
            controller=controller,
            workers=workers_sorted,
            pid_records_missing=pid_records_missing,
            pid_records_stale=pid_records_stale,
            fallback_used=fallback_used,
        )

    def _select_worker_sg(self, settings: CmtsOrchestratorSettings) -> ServiceGroupId | None:
        if settings.mode != OrchestratorMode.WORKER:
            return None
        for entry in settings.service_groups:
            if bool(entry.enabled):
                return entry.sg_id
        return None

    def _ensure_state_dir_exists(self, state_dir: Path) -> bool:
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def _ensure_state_subdirs(self, state_dir: Path) -> bool:
        try:
            for name in self.READY_SUBDIRS:
                (state_dir / name).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def _ensure_state_dir_writable(self, state_dir: Path) -> bool:
        try:
            test_dir = state_dir / self.READY_PROBE_DIR_NAME
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / f"{self.READY_PROBE_FILE_PREFIX}.{os.getpid()}"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            with contextlib.suppress(Exception):
                test_dir.rmdir()
            return True
        except Exception:
            return False

    def _ensure_state_dir_readable(self, state_dir: Path) -> bool:
        if not state_dir.is_dir():
            return False
        try:
            for _ in state_dir.iterdir():
                break
            return True
        except Exception:
            return False

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _collect_pidfile_status(
        self, state_dir: Path
    ) -> tuple[OperationalProcessInfoModel, list[OperationalProcessInfoModel], bool, bool]:
        pid_dir = state_dir / self.PID_DIR_NAME
        if not pid_dir.exists() or not pid_dir.is_dir():
            return (
                OperationalProcessInfoModel(),
                [],
                True,
                False,
            )

        pid_files = list(pid_dir.glob("*.pid"))
        if not pid_files:
            return (
                OperationalProcessInfoModel(),
                [],
                True,
                False,
            )

        controller_info = OperationalProcessInfoModel()
        worker_infos: list[OperationalProcessInfoModel] = []
        running_found = False

        for pid_path in pid_files:
            if pid_path.name == self.CONTROLLER_PID_NAME:
                controller_info = self._pidfile_info(pid_path, None)
                if controller_info.is_running:
                    running_found = True
                continue

            if pid_path.name == f"{self.UNBOUND_WORKER_NAME}{self.PID_SUFFIX}":
                info = self._pidfile_info(pid_path, None)
                worker_infos.append(info)
                if info.is_running:
                    running_found = True
                continue

            if pid_path.name.startswith(self.WORKER_PID_PREFIX) and pid_path.name.endswith(
                self.PID_SUFFIX
            ):
                sg_value = self._parse_worker_pid_sg(pid_path.name)
                info = self._pidfile_info(pid_path, sg_value)
                worker_infos.append(info)
                if info.is_running:
                    running_found = True
                continue

            info = self._pidfile_info(pid_path, None)
            worker_infos.append(info)
            if info.is_running:
                running_found = True

        pid_records_missing = False
        pid_records_stale = not running_found
        return (controller_info, worker_infos, pid_records_missing, pid_records_stale)

    def _pidfile_info(
        self,
        pid_path: Path,
        sg_id: ServiceGroupId | None,
    ) -> OperationalProcessInfoModel:
        pid_value = None
        try:
            text_value = pid_path.read_text(encoding="utf-8").strip()
            if text_value != "":
                pid_value = int(text_value)
        except Exception:
            pid_value = None

        is_running = False
        if pid_value is not None:
            is_running = self._pid_is_running(pid_value)

        return OperationalProcessInfoModel(
            pidfile_path=str(pid_path),
            pidfile_exists=True,
            pid=pid_value,
            is_running=is_running,
            sg_id=sg_id,
        )

    def _pid_is_running(self, pid_value: int) -> bool:
        try:
            os.kill(pid_value, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False

    def _parse_worker_pid_sg(self, filename: str) -> ServiceGroupId | None:
        name = filename
        if not name.startswith(self.WORKER_PID_PREFIX):
            return None
        if not name.endswith(self.PID_SUFFIX):
            return None
        raw = name[len(self.WORKER_PID_PREFIX) : -len(self.PID_SUFFIX)]
        if raw == "unbound":
            return None
        try:
            return ServiceGroupId(int(raw))
        except Exception:
            return None

    def _apply_fallback_process_scan(
        self,
        election_name: CoordinationElectionName | None,
        controller: OperationalProcessInfoModel,
        workers: list[OperationalProcessInfoModel],
    ) -> tuple[bool, OperationalProcessInfoModel, list[OperationalProcessInfoModel]]:
        election_value = ""
        if election_name is not None:
            election_value = str(election_name).strip()
        if election_value == "":
            return (False, controller, workers)

        candidates = self._fallback_find_processes(election_value)
        if not candidates:
            return (False, controller, workers)

        controller_info = controller
        worker_infos = list(workers)

        for pid_value, args_text in candidates:
            mode_value = self._extract_arg_value(args_text, "--mode")
            sg_value = self._extract_arg_value(args_text, "--sg-id")
            sg_id = None
            if sg_value != "":
                try:
                    sg_id = ServiceGroupId(int(sg_value))
                except Exception:
                    sg_id = None

            info = OperationalProcessInfoModel(
                pidfile_path=None,
                pidfile_exists=False,
                pid=pid_value,
                is_running=self._pid_is_running(pid_value),
                sg_id=sg_id,
            )

            if mode_value == "controller":
                controller_info = info
            elif mode_value == "worker":
                worker_infos.append(info)
            else:
                worker_infos.append(info)

        return (True, controller_info, worker_infos)

    def _fallback_find_processes(self, election_name: str) -> list[tuple[int, str]]:
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid,args"],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            return []

        stdout = result.stdout or ""
        lines = stdout.splitlines()
        matches: list[tuple[int, str]] = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split(maxsplit=1)
            if len(parts) != 2:
                continue
            try:
                pid_value = int(parts[0])
            except Exception:
                continue
            args_text = parts[1]
            if "pypnm-cmts" not in args_text:
                continue
            if "run-forever" not in args_text:
                continue
            election_value = self._extract_arg_value(args_text, "--election-name")
            if election_value == "":
                continue
            if election_value != election_name:
                continue
            matches.append((pid_value, args_text))
        return matches

    def _extract_arg_value(self, args_text: str, arg_name: str) -> str:
        try:
            tokens = shlex.split(args_text)
        except Exception:
            return ""
        for idx, token in enumerate(tokens):
            if token == arg_name:
                if idx + 1 < len(tokens):
                    return tokens[idx + 1]
                return ""
            if token.startswith(f"{arg_name}="):
                return token[len(arg_name) + 1 :]
        return ""


__all__ = [
    "OperationalService",
]

FILE: src/pypnm_cmts/api/routes/operational/schemas.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    ServiceGroupId,
)
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class OperationalIdentityModel(BaseModel):
    """Runtime identity metadata for operational endpoints."""

    mode: OrchestratorMode = Field(default=OrchestratorMode.STANDALONE, description="Current orchestrator mode.")
    election_name: CoordinationElectionName | None = Field(default=None, description="Election name for coordination.")
    state_dir: CoordinationPath | None = Field(default=None, description="Coordination state directory.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Bound service group id for worker mode.")


class HealthResponseModel(BaseModel):
    """Health endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Health status indicator.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")


class ReadyResponseModel(BaseModel):
    """Readiness endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Readiness status indicator.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    failed_check: ReadinessCheck | None = Field(default=None, description="Name of the first failing readiness check.")
    message: str = Field(default="", description="Human-readable readiness message.")


class OperationalProcessInfoModel(BaseModel):
    """Operational process snapshot for controller and worker processes."""

    pidfile_path: CoordinationPath | None = Field(default=None, description="PID file path for the process.")
    pidfile_exists: bool = Field(default=False, description="Whether the PID file exists.")
    pid: int | None = Field(default=None, description="PID value if available.")
    is_running: bool = Field(default=False, description="Whether the PID is currently running.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Service group id derived from pidfile naming.")


class OperationalStatusResponseModel(BaseModel):
    """Operational status endpoint response."""

    status: OperationalStatus = Field(default=OperationalStatus.OK, description="Operational status indicator.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")
    controller: OperationalProcessInfoModel = Field(default_factory=OperationalProcessInfoModel, description="Controller process snapshot.")
    workers: list[OperationalProcessInfoModel] = Field(default_factory=list, description="Worker process snapshots.")
    pid_records_missing: bool = Field(default=False, description="True when pidfiles are missing from state_dir.")
    pid_records_stale: bool = Field(default=False, description="True when pidfiles exist but none are running.")
    fallback_used: bool = Field(default=False, description="True when fallback discovery returns matching processes.")


class VersionResponseModel(BaseModel):
    """Version endpoint response."""

    application: str = Field(default="pypnm-cmts", description="Application name.")
    version: str = Field(default="", description="Package version string.")
    python_version: str = Field(default="", description="Python interpreter version.")
    build_metadata: str = Field(default="", description="Optional build metadata string.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")
    meta: OperationalIdentityModel = Field(default_factory=OperationalIdentityModel, description="Runtime identity metadata.")


__all__ = [
    "OperationalIdentityModel",
    "HealthResponseModel",
    "ReadyResponseModel",
    "OperationalProcessInfoModel",
    "OperationalStatusResponseModel",
    "VersionResponseModel",
]

FILE: tests/test_pidfile_manager.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.pidfile_manager import PidFileRecord


def test_pidfile_written_and_removed_controller(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.getpid", lambda: 12345)
    record = PidFileRecord.for_controller(tmp_path)
    with record:
        assert record.pidfile_path.exists()
        assert record.pidfile_path.read_text(encoding="utf-8").strip() == "12345"
    assert not record.pidfile_path.exists()


def test_pidfile_written_worker_with_sg_id(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.getpid", lambda: 22222)
    record = PidFileRecord.for_worker(tmp_path, ServiceGroupId(7))
    with record:
        assert record.pidfile_path.exists()
        assert record.pidfile_path.read_text(encoding="utf-8").strip() == "22222"
    assert not record.pidfile_path.exists()


def test_pidfile_cleanup_best_effort_does_not_raise(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    record = PidFileRecord.for_controller(tmp_path)
    with record:
        assert record.pidfile_path.exists()

    def _raise_unlink(self: Path) -> None:
        raise OSError("unlink failed")

    record.pidfile_path.write_text("999\n", encoding="utf-8")
    monkeypatch.setattr(Path, "unlink", _raise_unlink)
    record.__exit__(None, None, None)
    assert record.pidfile_path.exists()

FILE: tests/test_ops_service_smoke.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_version(base_url: str, timeout_seconds: float) -> httpx.Response | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/ops/version", timeout=2.0)
        except httpx.RequestError:
            time.sleep(0.1)
            continue

        if response.status_code == 200:
            return response

        time.sleep(0.1)
    return None


def test_ops_version_smoke_starts_service() -> None:
    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pypnm_cmts.cli",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    try:
        response = _wait_for_version(base_url, timeout_seconds=12.0)
        assert response is not None
        payload = response.json()
        assert payload.get("application") == "pypnm-cmts"
        assert "version" in payload
        assert "python_version" in payload
    finally:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)

FILE: tests/test_api_operational.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pypnm_cmts.config.orchestrator_config import (
    CmtsOrchestratorSettings,
    ServiceGroupDescriptor,
)
from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__


def _load_app(settings: CmtsOrchestratorSettings, monkeypatch: object) -> FastAPI:
    from pypnm_cmts.api.routes.operational.router import router as operational_router

    app = FastAPI(title="PyPNM-CMTS Operational API", version=__version__)
    app.include_router(operational_router)

    def _fake_from_system_config(**_kwargs: object) -> CmtsOrchestratorSettings:
        return settings

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls, **_kwargs: _fake_from_system_config()),
    )
    return app


def _client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _build_settings(
    mode: OrchestratorMode,
    state_dir: Path,
    service_groups: list[ServiceGroupDescriptor],
    election_name: str | None = None,
) -> CmtsOrchestratorSettings:
    payload = {
        "mode": mode,
        "state_dir": str(state_dir),
        "service_groups": [entry.model_dump() for entry in service_groups],
        "default_tests": ["test-a"],
    }
    if election_name is not None:
        payload["election_name"] = election_name
    return CmtsOrchestratorSettings.model_validate(payload)


def test_ops_health_returns_ok(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "state"
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        [],
        election_name="ops-demo",
    )
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["timestamp"] != ""
    assert payload["meta"]["mode"] == OrchestratorMode.STANDALONE
    assert payload["meta"]["state_dir"] == str(state_dir)
    assert payload["meta"]["election_name"] == "ops-demo"


def test_ops_version_returns_metadata(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "state"
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        [],
        election_name="ops-version",
    )
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["application"] == "pypnm-cmts"
    assert payload["version"] == __version__
    assert payload["python_version"] != ""
    assert payload["timestamp"] != ""
    assert payload["meta"]["state_dir"] == str(state_dir)
    assert payload["meta"]["election_name"] == "ops-version"


def test_ops_ready_controller_creates_state_dir(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert state_dir.exists()
    assert (state_dir / "pids").exists()
    assert (state_dir / "logs").exists()
    assert (state_dir / "inventory").exists()


def test_ops_ready_controller_not_writable(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    from pypnm_cmts.api.routes.operational.service import OperationalService

    monkeypatch.setattr(OperationalService, "_ensure_state_dir_writable", lambda *_args: False)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["failed_check"] == ReadinessCheck.STATE_DIR_ACCESS.value
    assert body["status"] == OperationalStatus.ERROR.value


def test_ops_ready_worker_requires_sg(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    state_dir.mkdir(parents=True, exist_ok=True)
    settings = _build_settings(OrchestratorMode.WORKER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["failed_check"] == ReadinessCheck.WORKER_SG.value


def test_ops_ready_worker_ok(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    state_dir.mkdir(parents=True, exist_ok=True)
    service_groups = [ServiceGroupDescriptor(sg_id=1, name="sg-1", enabled=True)]
    settings = _build_settings(OrchestratorMode.WORKER, state_dir, service_groups)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["meta"]["sg_id"] == service_groups[0].sg_id


def test_ops_status_missing_pid_records(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["pid_records_missing"] is True
    assert payload["pid_records_stale"] is False
    assert payload["fallback_used"] is False


def test_ops_status_pidfile_parsing(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    pid_dir = state_dir / "pids"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "controller.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_5.pid").write_text("999999", encoding="utf-8")
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pid_records_missing"] is False
    assert payload["pid_records_stale"] is True
    assert payload["controller"]["pidfile_exists"] is True
    assert payload["controller"]["pid"] == 999999
    assert payload["controller"]["is_running"] is False
    assert payload["workers"][0]["pidfile_exists"] is True
    assert payload["workers"][0]["pid"] == 999999
    assert payload["workers"][0]["is_running"] is False
    assert payload["workers"][0]["sg_id"] == 5


def test_ops_status_skips_fallback_without_election(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(
        OrchestratorMode.CONTROLLER,
        state_dir,
        [],
        election_name=None,
    )
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is False


def test_ops_status_worker_sorting(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    pid_dir = state_dir / "pids"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "controller.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_10.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_2.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_unbound.pid").write_text("999999", encoding="utf-8")
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    workers = payload["workers"]
    assert workers[0]["sg_id"] == 2
    assert workers[1]["sg_id"] == 10
    assert workers[2]["sg_id"] is None


def test_ops_status_fallback_arg_equals_parsing(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(
        OrchestratorMode.CONTROLLER,
        state_dir,
        [],
        election_name="ops-demo",
    )
    app = _load_app(settings, monkeypatch)
    from pypnm_cmts.api.routes.operational.service import OperationalService

    def _fake_fallback(_self: OperationalService, _election: str) -> list[tuple[int, str]]:
        return [
            (
                999999,
                "pypnm-cmts run-forever --election-name=ops-demo --mode=worker --sg-id=7",
            )
        ]

    monkeypatch.setattr(OperationalService, "_fallback_find_processes", _fake_fallback)

    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is True
    workers = payload["workers"]
    assert len(workers) == 1
    assert workers[0]["sg_id"] == 7
    assert workers[0]["pidfile_exists"] is False

FILE: docs/api/fast-api/operational.md
# Operational Endpoints

Read-Only Operational Endpoints For Health, Readiness, And Version.
All responses include the common `meta` identity block (mode, election_name, state_dir, sg_id).

## Endpoints

### GET /ops/health

Liveness Probe.
Always returns HTTP 200 if the process is running.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/health
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

### GET /ops/ready

Readiness Probe.
Returns HTTP 200 when local prerequisites are satisfied, otherwise HTTP 503 with a structured body.

Readiness checks:

- Controller: state_dir exists or can be created, required subdirectories can be created, and state_dir is writable.
- Worker: state_dir exists and is readable, and sg_id is bound.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/ready
```

Response shape (ready):

```json
{
  "status": "ok",
  "failed_check": null,
  "message": "",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

Response shape (not ready):

```json
{
  "status": "error",
  "failed_check": "state_dir_access",
  "message": "state_dir is not writable: .data/coordination",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

### GET /ops/status

Read-Only Operational Status Snapshot.
Reports controller and worker process visibility and PID record state.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/status
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "controller": {
    "pidfile_path": ".data/coordination/pids/controller.pid",
    "pidfile_exists": true,
    "pid": 12345,
    "is_running": true,
    "sg_id": null
  },
  "workers": [
    {
      "pidfile_path": ".data/coordination/pids/worker_1.pid",
      "pidfile_exists": true,
      "pid": 23456,
      "is_running": true,
      "sg_id": 1
    }
  ],
  "pid_records_missing": false,
  "pid_records_stale": false,
  "fallback_used": false
}
```

Notes:

- pid_records_missing is true when the pids directory is missing or empty.
- pid_records_stale is true when pidfiles exist but none of the recorded PIDs are running.
- fallback_used is true only when fallback discovery finds processes with an exact --election-name match.
- workers are sorted by sg_id ascending, with unbound workers listed last; ties break by pid then pidfile_path.

### GET /ops/version

Service Identity, Version, And Runtime Metadata.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/version
```

Response shape:

```json
{
  "application": "pypnm-cmts",
  "version": "0.1.0",
  "python_version": "3.10.12",
  "build_metadata": "",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

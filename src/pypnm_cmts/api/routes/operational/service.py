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

        if meta.mode in (OrchestratorMode.CONTROLLER, OrchestratorMode.STANDALONE):
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

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
import threading
from pathlib import Path
from uuid import uuid4

from pypnm.lib.types import TimestampSec
from pypnm.lib.utils import Generate, TimeUnit

from pypnm_cmts.api.common.operations.models import (
    OperationRequestContextModel,
    OperationRequestSummaryModel,
    OperationStateModel,
    OperationTimestampsModel,
    PerModemLinkageRecordModel,
)
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings
from pypnm_cmts.lib.constants import OperationState
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId

STATE_FILE_NAME = "state.json"
REQUEST_CONTEXT_FILE_NAME = "request_context.json"
CANCEL_FLAG_NAME = "cancel.flag"
RESULTS_DIR_NAME = "results"
RESULT_FILE_PREFIX = "sg-"
RESULT_FILE_SUFFIX = ".jsonl"
FALLBACK_BASE_DIR = Path("sg_operations")


class OperationStore:
    """Filesystem-backed store for operation state and linkage records."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or self._default_base_dir()
        self._state_lock = threading.Lock()

    def create_operation(
        self,
        request_summary: OperationRequestSummaryModel,
        request_context: OperationRequestContextModel | None = None,
    ) -> OperationStateModel:
        """Create a new operation directory and persist initial state."""
        operation_id = self._generate_operation_id()
        now_epoch = self._now_epoch()
        timestamps = OperationTimestampsModel(
            created_epoch=now_epoch,
            started_epoch=TimestampSec(0),
            updated_epoch=now_epoch,
            finished_epoch=TimestampSec(0),
        )
        state = OperationStateModel(
            operation_id=operation_id,
            state=OperationState.QUEUED,
            timestamps=timestamps,
            request_summary=request_summary,
        )
        self._ensure_operation_dirs(operation_id)
        self.save_state_atomic(state)
        if request_context is not None:
            self.save_request_context(operation_id, request_context)
        return state

    def load_state(self, operation_id: PnmCaptureOperationId) -> OperationStateModel:
        """Load operation state from disk."""
        path = self._state_path(operation_id)
        if not path.exists():
            raise FileNotFoundError(f"operation state not found: {path}")
        with self._state_lock:
            payload = json.loads(path.read_text(encoding="utf-8"))
        return OperationStateModel.model_validate(payload)

    def save_state_atomic(self, state: OperationStateModel) -> None:
        """Persist operation state with an atomic file replace."""
        path = self._state_path(state.operation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".{uuid4().hex}.tmp")
        with self._state_lock:
            if path.exists():
                current_payload = json.loads(path.read_text(encoding="utf-8"))
                current_state = OperationStateModel.model_validate(current_payload)
                if not self._can_replace_state(current_state.state, state.state):
                    return
            tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
            tmp_path.replace(path)

    def save_request_context(
        self,
        operation_id: PnmCaptureOperationId,
        context: OperationRequestContextModel,
    ) -> None:
        """Persist request context overrides to disk."""
        path = self._request_context_path(operation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".{uuid4().hex}.tmp")
        with self._state_lock:
            tmp_path.write_text(context.model_dump_json(indent=2), encoding="utf-8")
            tmp_path.replace(path)

    def load_request_context(
        self,
        operation_id: PnmCaptureOperationId,
    ) -> OperationRequestContextModel | None:
        """Load request context overrides if present."""
        path = self._request_context_path(operation_id)
        if not path.exists():
            return None
        with self._state_lock:
            payload = json.loads(path.read_text(encoding="utf-8"))
        return OperationRequestContextModel.model_validate(payload)

    def request_cancel(self, operation_id: PnmCaptureOperationId) -> OperationStateModel:
        """Create cancel.flag and update state unless already terminal."""
        state = self.load_state(operation_id)
        if self._is_terminal_state(state.state):
            return state
        self._cancel_flag_path(operation_id).touch(exist_ok=True)
        updated = state.model_copy(
            update={
                "state": OperationState.CANCELLING,
                "timestamps": state.timestamps.model_copy(
                    update={
                        "updated_epoch": self._now_epoch(),
                    }
                ),
            }
        )
        self.save_state_atomic(updated)
        return updated

    def is_cancel_requested(self, operation_id: PnmCaptureOperationId) -> bool:
        """Return whether the cancel flag exists for the operation."""
        return self._cancel_flag_path(operation_id).exists()

    def append_result_record(self, record: PerModemLinkageRecordModel) -> None:
        """Append a JSONL linkage record for the specified service group."""
        path = self._result_path(record.pnm_capture_operation_id, record.sg_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = record.model_dump_json()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    def count_result_files(self, operation_id: PnmCaptureOperationId) -> int:
        """Count JSONL result files for the operation."""
        return len(self._list_result_files(operation_id))

    def load_result_records(
        self,
        operation_id: PnmCaptureOperationId,
        max_records: int | None = None,
    ) -> list[PerModemLinkageRecordModel]:
        """Load linkage records from JSONL files, bounded by max_records."""
        records: list[PerModemLinkageRecordModel] = []
        for path in self._list_result_files(operation_id):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if max_records is not None and len(records) >= max_records:
                        return records
                    trimmed = line.strip()
                    if trimmed == "":
                        continue
                    records.append(PerModemLinkageRecordModel.model_validate_json(trimmed))
        return records

    def count_result_records(self, operation_id: PnmCaptureOperationId) -> int:
        """Count linkage records across all JSONL result files."""
        count = 0
        for path in self._list_result_files(operation_id):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip() != "":
                        count += 1
        return count

    def _ensure_operation_dirs(self, operation_id: PnmCaptureOperationId) -> None:
        base = self._operation_dir(operation_id)
        base.mkdir(parents=True, exist_ok=True)
        self._results_dir(operation_id).mkdir(parents=True, exist_ok=True)

    def _operation_dir(self, operation_id: PnmCaptureOperationId) -> Path:
        return self._base_dir / str(operation_id)

    def _results_dir(self, operation_id: PnmCaptureOperationId) -> Path:
        return self._operation_dir(operation_id) / RESULTS_DIR_NAME

    def _state_path(self, operation_id: PnmCaptureOperationId) -> Path:
        return self._operation_dir(operation_id) / STATE_FILE_NAME

    def _request_context_path(self, operation_id: PnmCaptureOperationId) -> Path:
        return self._operation_dir(operation_id) / REQUEST_CONTEXT_FILE_NAME

    def _cancel_flag_path(self, operation_id: PnmCaptureOperationId) -> Path:
        return self._operation_dir(operation_id) / CANCEL_FLAG_NAME

    def _result_path(self, operation_id: PnmCaptureOperationId, sg_id: ServiceGroupId) -> Path:
        name = f"{RESULT_FILE_PREFIX}{int(sg_id)}{RESULT_FILE_SUFFIX}"
        return self._results_dir(operation_id) / name

    def _list_result_files(self, operation_id: PnmCaptureOperationId) -> list[Path]:
        results_dir = self._results_dir(operation_id)
        if not results_dir.exists():
            return []
        return sorted(results_dir.glob(f"{RESULT_FILE_PREFIX}*{RESULT_FILE_SUFFIX}"))

    @staticmethod
    def _generate_operation_id() -> PnmCaptureOperationId:
        return PnmCaptureOperationId(str(Generate.operation_id()))

    @staticmethod
    def _default_base_dir() -> Path:
        try:
            return CmtsSystemConfigSettings.sg_operations_dir()
        except Exception:
            return FALLBACK_BASE_DIR

    @staticmethod
    def _now_epoch() -> TimestampSec:
        return TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))

    @staticmethod
    def _is_terminal_state(state: OperationState) -> bool:
        return state in {
            OperationState.COMPLETED,
            OperationState.FAILED,
            OperationState.CANCELLED,
        }

    @classmethod
    def _can_replace_state(cls, current: OperationState, incoming: OperationState) -> bool:
        if cls._is_terminal_state(current):
            return current == incoming
        return True


__all__ = [
    "OperationStore",
]

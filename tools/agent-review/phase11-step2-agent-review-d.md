# FILE: src/pypnm_cmts/api/common/operations/store.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pypnm.lib.types import TimestampSec
from pypnm.lib.utils import Generate, TimeUnit

from pypnm_cmts.api.common.operations.models import (
    OperationRequestSummaryModel,
    OperationStateModel,
    OperationTimestampsModel,
    PerModemLinkageRecordModel,
)
from pypnm_cmts.lib.constants import OperationState
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId

STATE_FILE_NAME = "state.json"
CANCEL_FLAG_NAME = "cancel.flag"
RESULTS_DIR_NAME = "results"
RESULT_FILE_PREFIX = "sg-"
RESULT_FILE_SUFFIX = ".jsonl"
DEFAULT_BASE_DIR = Path(".data/sg_operations")


class OperationStore:
    """Filesystem-backed store for operation state and linkage records."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or DEFAULT_BASE_DIR

    def create_operation(self, request_summary: OperationRequestSummaryModel) -> OperationStateModel:
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
        return state

    def load_state(self, operation_id: PnmCaptureOperationId) -> OperationStateModel:
        """Load operation state from disk."""
        path = self._state_path(operation_id)
        if not path.exists():
            raise FileNotFoundError(f"operation state not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return OperationStateModel.model_validate(payload)

    def save_state_atomic(self, state: OperationStateModel) -> None:
        """Persist operation state with an atomic file replace."""
        path = self._state_path(state.operation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        tmp_path.replace(path)

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
        return PnmCaptureOperationId(uuid4().hex)

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


__all__ = [
    "OperationStore",
]

# FILE: tests/test_rxmer_orchestration.py
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import FileNameStr, InetAddressStr, MacAddressStr, TransactionId

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsPnmCaptureParametersModel,
    CmtsPnmParametersModel,
    CmtsRequestEnvelopeModel,
    CmtsSnmpModel,
    CmtsSnmpV2CModel,
    CmtsTftpParametersModel,
)
from pypnm_cmts.api.common.operations.models import PerModemLinkageRecordModel
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.routes.pnm.rxmer.schemas import (
    RxMerServiceGroupExecutionModel,
    RxMerServiceGroupOperationRequest,
    RxMerServiceGroupStartCaptureRequest,
)
from pypnm_cmts.api.routes.pnm.rxmer.service import RxMerServiceGroupOperationService
from pypnm_cmts.lib.constants import OperationStage, OperationState
from pypnm_cmts.lib.types import ServiceGroupId


def _build_service(tmp_path: Path) -> RxMerServiceGroupOperationService:
    store = OperationStore(base_dir=tmp_path)
    return RxMerServiceGroupOperationService(store=store)


def test_rxmer_start_capture_creates_state(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = RxMerServiceGroupStartCaptureRequest()
    response = service.start_capture(request)

    operation = response.operation
    assert operation.state == OperationState.QUEUED

    state_path = tmp_path / str(operation.operation_id) / "state.json"
    assert state_path.exists()


def test_rxmer_status_reads_state(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = RxMerServiceGroupStartCaptureRequest()
    start_response = service.start_capture(request)

    status_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    status_response = service.status(status_request)
    assert status_response.operation is not None
    assert status_response.operation.operation_id == start_response.operation.operation_id


def test_rxmer_cancel_creates_flag(tmp_path: Path) -> None:
    store = OperationStore(base_dir=tmp_path)
    service = RxMerServiceGroupOperationService(store=store)
    request = RxMerServiceGroupStartCaptureRequest()
    start_response = service.start_capture(request)

    cancel_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    cancel_response = service.cancel(cancel_request)
    assert cancel_response.operation is not None
    assert cancel_response.operation.state == OperationState.CANCELLING
    assert store.is_cancel_requested(start_response.operation.operation_id)


def test_rxmer_results_empty(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = RxMerServiceGroupStartCaptureRequest()
    start_response = service.start_capture(request)

    results_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    results_response = service.results(results_request)
    assert results_response.summary.record_count == 0
    assert results_response.records == []


def test_rxmer_results_include_records(tmp_path: Path) -> None:
    store = OperationStore(base_dir=tmp_path)
    service = RxMerServiceGroupOperationService(store=store)
    request = RxMerServiceGroupStartCaptureRequest()
    start_response = service.start_capture(request)

    record = PerModemLinkageRecordModel(
        pnm_capture_operation_id=start_response.operation.operation_id,
        sg_id=ServiceGroupId(1),
        mac_address=MacAddressStr("aa:bb:cc:dd:ee:ff"),
        ip_address=InetAddressStr("192.168.0.100"),
        stage=OperationStage.ELIGIBILITY,
        status_code=ServiceStatusCode.SUCCESS,
        transaction_ids=[TransactionId("1a2b3c4d5e6f7a8b9c0d1e2f")],
        filenames=[FileNameStr("capture.bin")],
        started_epoch=1,
        finished_epoch=2,
        message="",
    )
    store.append_result_record(record)

    results_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    results_response = service.results(results_request)
    assert results_response.summary.record_count == 1
    assert len(results_response.records) == 1


def test_rxmer_request_rejects_blank_snmp_community() -> None:
    with pytest.raises(ValidationError):
        RxMerServiceGroupStartCaptureRequest(
            cmts=CmtsRequestEnvelopeModel(
                cable_modem=CmtsCableModemFilterModel(
                    snmp=CmtsSnmpModel(
                        snmpV2C=CmtsSnmpV2CModel(community=""),
                    ),
                )
            )
        )


def test_rxmer_request_allows_null_snmp_community() -> None:
    request = RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            cable_modem=CmtsCableModemFilterModel(
                snmp=CmtsSnmpModel(
                    snmpV2C=CmtsSnmpV2CModel(community=None),
                ),
            )
        )
    )
    assert request.cmts.cable_modem.snmp is not None


def test_rxmer_request_rejects_blank_tftp_overrides() -> None:
    with pytest.raises(ValidationError):
        RxMerServiceGroupStartCaptureRequest(
            cmts=CmtsRequestEnvelopeModel(
                cable_modem=CmtsCableModemFilterModel(
                    pnm_parameters=CmtsPnmParametersModel(
                        tftp=CmtsTftpParametersModel(ipv4="", ipv6=None),
                    )
                )
            )
        )


def test_rxmer_request_allows_null_tftp_overrides() -> None:
    request = RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            cable_modem=CmtsCableModemFilterModel(
                pnm_parameters=CmtsPnmParametersModel(
                    tftp=CmtsTftpParametersModel(ipv4=None, ipv6=None),
                    capture=CmtsPnmCaptureParametersModel(channel_ids=[]),
                )
            )
        )
    )
    assert request.cmts.cable_modem.pnm_parameters is not None


def test_rxmer_execution_validation_rules() -> None:
    with pytest.raises(ValidationError):
        RxMerServiceGroupExecutionModel(
            max_workers=-1,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        RxMerServiceGroupExecutionModel(
            max_workers=0,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=0.0,
            overall_timeout_seconds=1.0,
        )


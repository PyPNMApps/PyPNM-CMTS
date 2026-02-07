# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import (
    FileNameStr,
    InetAddressStr,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    TimestampSec,
    TransactionId,
)
from pypnm.lib.utils import Generate, TimeUnit

import pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.service as rxmer_service_module
from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsPnmCaptureParametersModel,
    CmtsPnmParametersModel,
    CmtsRequestEnvelopeModel,
    CmtsServingGroupFilterModel,
    CmtsSnmpModel,
    CmtsSnmpV2CModel,
    CmtsTftpParametersModel,
)
from pypnm_cmts.api.common.operations.models import (
    OperationStageResultModel,
    PerModemLinkageRecordModel,
)
from pypnm_cmts.api.common.operations.runner import (
    DEFAULT_OVERALL_TIMEOUT_MESSAGE,
    OperationRunner,
    OperationWorkerResultModel,
    OperationWorkItemModel,
)
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.schemas import (
    RxMerServiceGroupExecutionModel,
    RxMerServiceGroupOperationRequest,
    RxMerServiceGroupStartCaptureRequest,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.service import (
    RxMerServiceGroupOperationService,
)
from pypnm_cmts.lib.constants import OperationStage, OperationState
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwSnapshotModel,
)
from pypnm_cmts.sgw.store import SgwCacheStore

POLL_INTERVAL_SECONDS = 0.02
STATE_TIMEOUT_SECONDS = 2.0
WORKER_DELAY_SECONDS = 0.1


def _build_service(
    tmp_path: Path,
    worker: Callable[[OperationWorkItemModel], OperationWorkerResultModel] | None = None,
    sgw_store: SgwCacheStore | None = None,
) -> RxMerServiceGroupOperationService:
    store = OperationStore(base_dir=tmp_path)
    runner = OperationRunner(store=store, worker=worker)
    return RxMerServiceGroupOperationService(store=store, runner=runner, sgw_store=sgw_store)


def _build_request(
    mac_count: int = 0,
    execution: RxMerServiceGroupExecutionModel | None = None,
) -> RxMerServiceGroupStartCaptureRequest:
    macs = [MacAddressStr(f"aa:bb:cc:dd:ee:{index:02x}") for index in range(mac_count)]
    return RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[ServiceGroupId(1)]),
            cable_modem=CmtsCableModemFilterModel(mac_address=macs),
        ),
        execution=execution or RxMerServiceGroupExecutionModel(),
    )


def _build_sgw_store(entries: list[tuple[ServiceGroupId, list[MacAddressStr]]]) -> SgwCacheStore:
    store = SgwCacheStore()
    for sg_id, mac_addresses in entries:
        cable_modems = [
            SgwCableModemModel(
                mac=mac_address,
                ipv4=IPv4Str("192.168.0.100"),
                ipv6=IPv6Str(""),
            )
            for mac_address in mac_addresses
        ]
        snapshot = SgwSnapshotModel(
            sg_id=sg_id,
            cable_modems=cable_modems,
        )
        store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))
    return store


def _wait_for_state(
    store: OperationStore,
    operation_id: PnmCaptureOperationId,
    targets: set[OperationState],
) -> OperationState | None:
    deadline = time.monotonic() + STATE_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        state = store.load_state(operation_id)
        if state.state in targets:
            return state.state
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


def _slow_worker(item: OperationWorkItemModel) -> OperationWorkerResultModel:
    started_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
    time.sleep(WORKER_DELAY_SECONDS)
    finished_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
    return OperationWorkerResultModel(
        stages=[
            OperationStageResultModel(
                stage=OperationStage.ELIGIBILITY,
                status_code=ServiceStatusCode.SUCCESS,
                transaction_ids=[],
                filenames=[],
                message="eligible",
                started_epoch=started_epoch,
                finished_epoch=finished_epoch,
            ),
            OperationStageResultModel(
                stage=OperationStage.PRECHECK,
                status_code=ServiceStatusCode.SUCCESS,
                transaction_ids=[],
                filenames=[],
                message="precheck ok",
                started_epoch=started_epoch,
                finished_epoch=finished_epoch,
            ),
            OperationStageResultModel(
                stage=OperationStage.CAPTURE,
                status_code=ServiceStatusCode.SUCCESS,
                transaction_ids=[TransactionId("1a2b3c4d5e6f7a8b9c0d1e2f")],
                filenames=[FileNameStr("capture.bin")],
                message="completed",
                started_epoch=started_epoch,
                finished_epoch=finished_epoch,
            ),
        ]
    )


def test_rxmer_start_capture_creates_state(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = _build_request()
    response = service.start_capture(request)

    operation = response.operation
    assert operation.state == OperationState.QUEUED

    state_path = tmp_path / str(operation.operation_id) / "state.json"
    assert state_path.exists()


def test_rxmer_status_reads_state(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = _build_request()
    start_response = service.start_capture(request)

    status_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    status_response = service.status(status_request)
    assert status_response.operation is not None
    assert status_response.operation.operation_id == start_response.operation.operation_id


def test_rxmer_cancel_creates_flag(tmp_path: Path) -> None:
    service = _build_service(tmp_path, worker=_slow_worker)
    request = _build_request(mac_count=2)
    start_response = service.start_capture(request)

    cancel_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    cancel_response = service.cancel(cancel_request)
    assert cancel_response.operation is not None
    assert cancel_response.operation.state in {OperationState.CANCELLING, OperationState.CANCELLED}
    assert service._store.is_cancel_requested(start_response.operation.operation_id)


def test_rxmer_results_empty(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = _build_request()
    start_response = service.start_capture(request)

    results_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    results_response = service.results(results_request)
    assert results_response.summary.record_count == 0
    assert results_response.records == []


def test_rxmer_results_include_records(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    request = _build_request()
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
    service._store.append_result_record(record)

    results_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    results_response = service.results(results_request)
    assert results_response.summary.record_count == 1
    assert len(results_response.records) == 1


def test_rxmer_runner_transitions_to_running(tmp_path: Path) -> None:
    service = _build_service(tmp_path, worker=_slow_worker)
    request = _build_request(mac_count=2)
    start_response = service.start_capture(request)

    running_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.RUNNING},
    )
    assert running_state == OperationState.RUNNING


def test_rxmer_runner_cancelled(tmp_path: Path) -> None:
    service = _build_service(tmp_path, worker=_slow_worker)
    request = _build_request(mac_count=2)
    start_response = service.start_capture(request)

    cancel_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    service.cancel(cancel_request)
    cancelled_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.CANCELLED},
    )
    assert cancelled_state == OperationState.CANCELLED


def test_rxmer_runner_emits_records(tmp_path: Path) -> None:
    service = _build_service(tmp_path, worker=_slow_worker)
    request = _build_request(mac_count=2)
    start_response = service.start_capture(request)

    terminal_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.COMPLETED, OperationState.FAILED},
    )
    assert terminal_state == OperationState.COMPLETED
    assert service._store.count_result_records(start_response.operation.operation_id) > 0


def test_rxmer_runner_no_modems_selected(tmp_path: Path) -> None:
    service = _build_service(tmp_path, worker=_slow_worker)
    request = _build_request(mac_count=0)
    start_response = service.start_capture(request)

    completed_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.COMPLETED},
    )
    assert completed_state == OperationState.COMPLETED
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.counters.total_modems == 0
    assert service._store.count_result_records(start_response.operation.operation_id) == 0


def test_rxmer_start_capture_expands_wildcard_sg_and_mac(tmp_path: Path) -> None:
    sg_one = ServiceGroupId(1)
    sg_two = ServiceGroupId(2)
    mac_one = MacAddressStr("aa:bb:cc:dd:ee:01")
    mac_two = MacAddressStr("aa:bb:cc:dd:ee:02")
    mac_three = MacAddressStr("aa:bb:cc:dd:ee:03")
    sgw_store = _build_sgw_store(
        entries=[
            (sg_one, [mac_one]),
            (sg_two, [mac_two, mac_three]),
        ]
    )
    service = _build_service(tmp_path, worker=_slow_worker, sgw_store=sgw_store)
    request = RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[]),
            cable_modem=CmtsCableModemFilterModel(mac_address=[]),
        ),
        execution=RxMerServiceGroupExecutionModel(max_workers=4),
    )

    start_response = service.start_capture(request)
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.request_summary.serving_group_ids == [sg_one, sg_two, sg_two]
    assert state.request_summary.mac_addresses == [mac_one, mac_two, mac_three]


def test_rxmer_start_capture_expands_wildcard_mac_for_selected_sg(tmp_path: Path) -> None:
    sg_one = ServiceGroupId(1)
    sg_two = ServiceGroupId(2)
    mac_one = MacAddressStr("aa:bb:cc:dd:ee:01")
    mac_two = MacAddressStr("aa:bb:cc:dd:ee:02")
    sgw_store = _build_sgw_store(
        entries=[
            (sg_one, [mac_one]),
            (sg_two, [mac_two]),
        ]
    )
    service = _build_service(tmp_path, worker=_slow_worker, sgw_store=sgw_store)
    request = RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[sg_two]),
            cable_modem=CmtsCableModemFilterModel(mac_address=[]),
        ),
        execution=RxMerServiceGroupExecutionModel(max_workers=2),
    )

    start_response = service.start_capture(request)
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.request_summary.serving_group_ids == [sg_two]
    assert state.request_summary.mac_addresses == [mac_two]


def test_rxmer_start_capture_expands_wildcard_sg_for_selected_mac(tmp_path: Path) -> None:
    sg_one = ServiceGroupId(1)
    sg_two = ServiceGroupId(2)
    target_mac = MacAddressStr("aa:bb:cc:dd:ee:aa")
    sgw_store = _build_sgw_store(
        entries=[
            (sg_one, [target_mac]),
            (sg_two, [MacAddressStr("aa:bb:cc:dd:ee:bb")]),
        ]
    )
    service = _build_service(tmp_path, worker=_slow_worker, sgw_store=sgw_store)
    request = RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[]),
            cable_modem=CmtsCableModemFilterModel(mac_address=[target_mac]),
        ),
        execution=RxMerServiceGroupExecutionModel(max_workers=2),
    )

    start_response = service.start_capture(request)
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.request_summary.serving_group_ids == [sg_one]
    assert state.request_summary.mac_addresses == [target_mac]


def test_rxmer_start_capture_refreshes_runtime_sgw_store_when_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sg_id = ServiceGroupId(7)
    mac = MacAddressStr("aa:bb:cc:dd:ee:07")
    runtime_store = _build_sgw_store(entries=[(sg_id, [mac])])
    service = _build_service(tmp_path, worker=_slow_worker, sgw_store=None)
    monkeypatch.setattr(rxmer_service_module, "get_sgw_store", lambda: runtime_store)
    request = RxMerServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[]),
            cable_modem=CmtsCableModemFilterModel(mac_address=[]),
        ),
        execution=RxMerServiceGroupExecutionModel(max_workers=1),
    )

    start_response = service.start_capture(request)
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.request_summary.serving_group_ids == [sg_id]
    assert state.request_summary.mac_addresses == [mac]


def test_rxmer_runner_retries_until_success(tmp_path: Path) -> None:
    attempts: dict[str, int] = {}

    def _flaky_worker(item: OperationWorkItemModel) -> OperationWorkerResultModel:
        count = attempts.get(str(item.mac_address), 0) + 1
        attempts[str(item.mac_address)] = count
        started_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
        finished_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
        if count == 1:
            return OperationWorkerResultModel(
                stages=[
                    OperationStageResultModel(
                        stage=OperationStage.ELIGIBILITY,
                        status_code=ServiceStatusCode.SUCCESS,
                        transaction_ids=[],
                        filenames=[],
                        message="eligible",
                        started_epoch=started_epoch,
                        finished_epoch=finished_epoch,
                    ),
                    OperationStageResultModel(
                        stage=OperationStage.PRECHECK,
                        status_code=ServiceStatusCode.SUCCESS,
                        transaction_ids=[],
                        filenames=[],
                        message="precheck ok",
                        started_epoch=started_epoch,
                        finished_epoch=finished_epoch,
                    ),
                    OperationStageResultModel(
                        stage=OperationStage.CAPTURE,
                        status_code=ServiceStatusCode.FAILURE,
                        transaction_ids=[],
                        filenames=[],
                        message="failed once",
                        started_epoch=started_epoch,
                        finished_epoch=finished_epoch,
                    ),
                ]
            )
        return OperationWorkerResultModel(
            stages=[
                OperationStageResultModel(
                    stage=OperationStage.ELIGIBILITY,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="eligible",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
                OperationStageResultModel(
                    stage=OperationStage.PRECHECK,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="precheck ok",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
                OperationStageResultModel(
                    stage=OperationStage.CAPTURE,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="recovered",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
            ]
        )

    service = _build_service(tmp_path, worker=_flaky_worker)
    request = _build_request(
        mac_count=1,
        execution=RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=1,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=2.0,
        ),
    )
    start_response = service.start_capture(request)
    terminal_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.COMPLETED, OperationState.FAILED},
    )
    assert terminal_state == OperationState.COMPLETED
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.counters.success == 1
    assert state.counters.failed == 0


def test_rxmer_runner_per_modem_timeout(tmp_path: Path) -> None:
    def _slow_timeout_worker(item: OperationWorkItemModel) -> OperationWorkerResultModel:
        started_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
        time.sleep(WORKER_DELAY_SECONDS)
        finished_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
        return OperationWorkerResultModel(
            stages=[
                OperationStageResultModel(
                    stage=OperationStage.ELIGIBILITY,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="eligible",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
                OperationStageResultModel(
                    stage=OperationStage.PRECHECK,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="precheck ok",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
                OperationStageResultModel(
                    stage=OperationStage.CAPTURE,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="late",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
            ]
        )

    service = _build_service(tmp_path, worker=_slow_timeout_worker)
    request = _build_request(
        mac_count=2,
        execution=RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=0.01,
            overall_timeout_seconds=2.0,
        ),
    )
    start_response = service.start_capture(request)
    terminal_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.COMPLETED, OperationState.FAILED},
    )
    assert terminal_state == OperationState.FAILED
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.counters.failed == 2
    assert state.counters.success == 0
    records = service._store.load_result_records(start_response.operation.operation_id)
    assert len(records) == 6
    stages = {record.stage for record in records}
    assert stages == {OperationStage.ELIGIBILITY, OperationStage.PRECHECK, OperationStage.CAPTURE}


def test_rxmer_runner_overall_timeout(tmp_path: Path) -> None:
    def _slow_overall_worker(item: OperationWorkItemModel) -> OperationWorkerResultModel:
        started_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
        time.sleep(WORKER_DELAY_SECONDS)
        finished_epoch = TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))
        return OperationWorkerResultModel(
            stages=[
                OperationStageResultModel(
                    stage=OperationStage.ELIGIBILITY,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="eligible",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
                OperationStageResultModel(
                    stage=OperationStage.PRECHECK,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="precheck ok",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
                OperationStageResultModel(
                    stage=OperationStage.CAPTURE,
                    status_code=ServiceStatusCode.SUCCESS,
                    transaction_ids=[],
                    filenames=[],
                    message="late",
                    started_epoch=started_epoch,
                    finished_epoch=finished_epoch,
                ),
            ]
        )

    service = _build_service(tmp_path, worker=_slow_overall_worker)
    request = _build_request(
        mac_count=2,
        execution=RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=0.05,
        ),
    )
    start_response = service.start_capture(request)
    terminal_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.FAILED},
    )
    assert terminal_state == OperationState.FAILED
    state = service._store.load_state(start_response.operation.operation_id)
    assert state.error_summary is not None
    assert DEFAULT_OVERALL_TIMEOUT_MESSAGE in state.error_summary.message


def test_rxmer_runner_cancel_mid_flight(tmp_path: Path) -> None:
    service = _build_service(tmp_path, worker=_slow_worker)
    request = _build_request(mac_count=5)
    start_response = service.start_capture(request)

    running_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.RUNNING},
    )
    assert running_state == OperationState.RUNNING

    cancel_request = RxMerServiceGroupOperationRequest(
        pnm_capture_operation_id=start_response.operation.operation_id,
    )
    service.cancel(cancel_request)
    cancelled_state = _wait_for_state(
        service._store,
        start_response.operation.operation_id,
        {OperationState.CANCELLED},
    )
    assert cancelled_state == OperationState.CANCELLED
    assert service._runner.is_running(start_response.operation.operation_id) is False


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
            max_workers=0,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=-1,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=0,
            retry_delay_seconds=-1.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=0.0,
            overall_timeout_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        RxMerServiceGroupExecutionModel(
            max_workers=1,
            retry_count=0,
            retry_delay_seconds=0.0,
            per_modem_timeout_seconds=1.0,
            overall_timeout_seconds=0.0,
        )

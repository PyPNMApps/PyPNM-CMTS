# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import time
from pathlib import Path

from pypnm.api.routes.common.extended.common_messaging_service import MessageResponse
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import IPv4Str, IPv6Str, MacAddressStr, TransactionId

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsRequestEnvelopeModel,
    CmtsServingGroupFilterModel,
)
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.routes.pnm.sg.us.ofdma.pre_equalization.schemas import (
    PreEqualizationServiceGroupExecutionModel,
    PreEqualizationServiceGroupStartCaptureRequest,
)
from pypnm_cmts.api.routes.pnm.sg.us.ofdma.pre_equalization.service import (
    PreEqualizationServiceGroupOperationService,
)
from pypnm_cmts.lib.constants import OperationStage, OperationState
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel, SgwCacheEntryModel, SgwSnapshotModel
from pypnm_cmts.sgw.store import SgwCacheStore

POLL_INTERVAL_SECONDS = 0.02
STATE_TIMEOUT_SECONDS = 3.0


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


def _build_sgw_store(mac_address: MacAddressStr, sg_id: ServiceGroupId) -> SgwCacheStore:
    store = SgwCacheStore()
    snapshot = SgwSnapshotModel(
        sg_id=sg_id,
        cable_modems=[
            SgwCableModemModel(
                mac=mac_address,
                ipv4=IPv4Str("192.168.0.100"),
                ipv6=IPv6Str(""),
            )
        ],
    )
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))
    return store


def test_us_pre_equalization_capture_records_two_files(tmp_path: Path) -> None:
    mac = MacAddressStr("aa:bb:cc:dd:ee:21")
    sg_id = ServiceGroupId(21)
    tx_one = TransactionId("111111111111111111111111")
    tx_two = TransactionId("222222222222222222222222")
    sgw_store = _build_sgw_store(mac, sg_id)

    def _fake_precheck(_cm) -> tuple[ServiceStatusCode, str]:
        return (ServiceStatusCode.SUCCESS, "precheck ok")

    def _fake_capture(_cm, _interface_parameters, _tftp_servers, _tftp_path) -> MessageResponse:
        payload = [
            {
                "status": ServiceStatusCode.SUCCESS.name,
                "message_type": "PNM_FILE_TRANSACTION",
                "message": {
                    "transaction_id": str(tx_one),
                    "filename": "pre-eq-a.bin",
                },
            },
            {
                "status": ServiceStatusCode.SUCCESS.name,
                "message_type": "PNM_FILE_TRANSACTION",
                "message": {
                    "transaction_id": str(tx_two),
                    "filename": "pre-eq-b.bin",
                },
            },
        ]
        return MessageResponse(ServiceStatusCode.SUCCESS, payload)

    service = PreEqualizationServiceGroupOperationService(
        store=OperationStore(base_dir=tmp_path / "ops"),
        capture_executor=_fake_capture,
        precheck_executor=_fake_precheck,
        sgw_store=sgw_store,
    )
    request = PreEqualizationServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[sg_id]),
            cable_modem=CmtsCableModemFilterModel(mac_address=[mac]),
        ),
        execution=PreEqualizationServiceGroupExecutionModel(
            max_workers=1,
            retry_count=0,
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

    records = service._store.load_result_records(start_response.operation.operation_id)
    capture_records = [record for record in records if record.stage == OperationStage.CAPTURE]
    assert capture_records
    assert capture_records[0].transaction_ids == [tx_one, tx_two]
    assert [str(name) for name in capture_records[0].filenames] == ["pre-eq-a.bin", "pre-eq-b.bin"]


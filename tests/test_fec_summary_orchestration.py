# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pypnm.api.routes.common.classes.common_endpoint_classes.common.enum import (
    OutputType,
)
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import (
    FileNameStr,
    InetAddressStr,
    MacAddressStr,
    TransactionId,
)

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsRequestEnvelopeModel,
    CmtsServingGroupFilterModel,
)
from pypnm_cmts.api.common.operations.models import PerModemLinkageRecordModel
from pypnm_cmts.api.common.operations.runner import OperationRunner
from pypnm_cmts.api.common.operations.store import OperationStore
from pypnm_cmts.api.common.service.pnm.results_analysis import (
    PnmStoredCaptureAnalysisResultModel,
    PnmStoredCaptureAnalysisService,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.schemas import (
    FecSummaryServiceGroupExecutionModel,
    FecSummaryServiceGroupOperationRequest,
    FecSummaryServiceGroupResultsRequest,
    FecSummaryServiceGroupStartCaptureRequest,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.service import (
    FecSummaryServiceGroupOperationService,
)
from pypnm_cmts.lib.constants import OperationStage
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId


def _build_service(
    tmp_path: Path,
    results_analysis_service: PnmStoredCaptureAnalysisService | None = None,
) -> FecSummaryServiceGroupOperationService:
    store = OperationStore(base_dir=tmp_path)
    runner = OperationRunner(store=store)
    return FecSummaryServiceGroupOperationService(
        store=store,
        runner=runner,
        results_analysis_service=results_analysis_service,
    )


def _build_request() -> FecSummaryServiceGroupStartCaptureRequest:
    return FecSummaryServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(
            serving_group=CmtsServingGroupFilterModel(id=[ServiceGroupId(1)]),
            cable_modem=CmtsCableModemFilterModel(mac_address=[]),
        ),
        execution=FecSummaryServiceGroupExecutionModel(),
    )


class _FakeResultsAnalysisService(PnmStoredCaptureAnalysisService):
    def __init__(self) -> None:
        self.calls: list[list[TransactionId]] = []

    def analyze_transactions_basic(
        self,
        transaction_ids: list[TransactionId],
    ) -> dict[TransactionId, PnmStoredCaptureAnalysisResultModel]:
        self.calls.append(list(transaction_ids))
        return {
            TransactionId("1a2b3c4d5e6f7a8b9c0d1e2f"): PnmStoredCaptureAnalysisResultModel(
                transaction_id=TransactionId("1a2b3c4d5e6f7a8b9c0d1e2f"),
                pnm_file_type="OFDM_FEC_SUMMARY",
                system_description={"VENDOR": "LANCity", "MODEL": "LCPET-3"},
                analysis={"channel_id": 160, "measurement_stats": []},
            )
        }


def test_fec_summary_results_empty(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    start_response = service.start_capture(_build_request())

    results_response = service.results(
        FecSummaryServiceGroupOperationRequest(
            pnm_capture_operation_id=start_response.operation.operation_id,
        )
    )

    assert results_response.summary.record_count == 0
    assert results_response.records == []
    assert results_response.results is not None
    assert results_response.results.capture_details.capture_type == "FEC_SUMMARY"
    assert results_response.results.channels == []
    assert results_response.results.serving_groups == []


def test_fec_summary_results_request_accepts_nested_operation_shape() -> None:
    request = FecSummaryServiceGroupResultsRequest.model_validate(
        {
            "operation": {"pnm_capture_operation_id": "6c83fb8c215081133c6bf041"},
            "output": {
                "type": "archive",
                "archive_includes": {"pnm_files": True, "png": True, "json": True},
            },
        }
    )
    assert request.operation.pnm_capture_operation_id == PnmCaptureOperationId("6c83fb8c215081133c6bf041")
    assert request.output.type == OutputType.ARCHIVE
    assert request.output.archive_includes is not None
    assert request.output.archive_includes.png is True


def test_fec_summary_results_request_coerces_legacy_flat_shape() -> None:
    request = FecSummaryServiceGroupResultsRequest.model_validate(
        {"pnm_capture_operation_id": "6c83fb8c215081133c6bf041"}
    )
    assert request.operation.pnm_capture_operation_id == PnmCaptureOperationId("6c83fb8c215081133c6bf041")
    assert request.output.type == OutputType.JSON
    assert request.output.archive_includes is None


def test_fec_summary_results_request_ignores_archive_includes_for_json_output() -> None:
    request = FecSummaryServiceGroupResultsRequest.model_validate(
        {
            "operation": {"pnm_capture_operation_id": "6c83fb8c215081133c6bf041"},
            "output": {"type": "json", "archive_includes": {"json": True}},
        }
    )
    assert request.output.type == OutputType.JSON
    assert request.output.archive_includes is None


def test_fec_summary_results_basic_analysis_decodes_via_common_service(tmp_path: Path) -> None:
    analysis_service = _FakeResultsAnalysisService()
    service = _build_service(tmp_path, results_analysis_service=analysis_service)
    start_response = service.start_capture(_build_request())

    service._store.append_result_record(
        PerModemLinkageRecordModel(
            pnm_capture_operation_id=start_response.operation.operation_id,
            sg_id=ServiceGroupId(1),
            mac_address=MacAddressStr("aa:bb:cc:dd:ee:ff"),
            ip_address=InetAddressStr("192.168.0.100"),
            stage=OperationStage.CAPTURE,
            status_code=ServiceStatusCode.SUCCESS,
            channel_id=None,
            transaction_ids=[TransactionId("1a2b3c4d5e6f7a8b9c0d1e2f")],
            filenames=[FileNameStr("capture.bin")],
            started_epoch=1,
            finished_epoch=2,
            message="",
        )
    )

    results_response = service.results(
        FecSummaryServiceGroupResultsRequest.model_validate(
            {
                "operation": {"pnm_capture_operation_id": str(start_response.operation.operation_id)},
                "analysis": {"type": "basic"},
                "output": {"type": "json"},
            }
        )
    )

    assert analysis_service.calls == [[TransactionId("1a2b3c4d5e6f7a8b9c0d1e2f")]]
    assert results_response.results is not None
    assert results_response.results.channels == []
    assert len(results_response.results.serving_groups) == 1
    channel = results_response.results.serving_groups[0].channels[0]
    assert channel.service_group_id == ServiceGroupId(1)
    assert channel.channel_id == 160
    modem = channel.cable_modems[0]
    assert modem.system_description is not None
    assert modem.system_description["VENDOR"] == "LANCity"
    assert modem.fec_summary_data.file is not None
    assert modem.fec_summary_data.file.transaction_id == "1a2b3c4d5e6f7a8b9c0d1e2f"
    assert modem.fec_summary_data.pnm_file_type == "OFDM_FEC_SUMMARY"
    assert modem.fec_summary_data.analysis is not None
    assert modem.fec_summary_data.analysis["channel_id"] == 160
    assert modem.fec_summary_data.analysis_error is None

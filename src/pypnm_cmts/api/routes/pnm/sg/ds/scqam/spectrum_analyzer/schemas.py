# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.docsis.cm_snmp_operation import SpectrumRetrievalType
from pypnm.lib.types import ResolutionBw

from pypnm_cmts.api.common.cmts_request import CmtsRequestEnvelopeModel
from pypnm_cmts.api.common.operations.models import (
    OperationResultsSummaryModel,
    OperationStateModel,
    PerModemLinkageRecordModel,
)
from pypnm_cmts.lib.types import PnmCaptureOperationId

DEFAULT_MAX_WORKERS = 16
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY_SECONDS = 5.0
DEFAULT_PER_MODEM_TIMEOUT_SECONDS = 30.0
DEFAULT_OVERALL_TIMEOUT_SECONDS = 120.0


class ScQamSpectrumAnalyzerServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group SCQAM SpectrumAnalyzer orchestration."""

    max_workers: int = Field(default=DEFAULT_MAX_WORKERS, gt=0, description="Maximum concurrent workers.")
    retry_count: int = Field(default=DEFAULT_RETRY_COUNT, ge=0, description="Retry attempts for retryable failures.")
    retry_delay_seconds: float = Field(
        default=DEFAULT_RETRY_DELAY_SECONDS,
        ge=0.0,
        description="Delay between retry attempts in seconds.",
    )
    per_modem_timeout_seconds: float = Field(
        default=DEFAULT_PER_MODEM_TIMEOUT_SECONDS,
        gt=0.0,
        description="Timeout for each modem in seconds.",
    )
    overall_timeout_seconds: float = Field(
        default=DEFAULT_OVERALL_TIMEOUT_SECONDS,
        gt=0.0,
        description="Overall timeout in seconds.",
    )


class ScQamSpectrumAnalyzerCaptureSettingsModel(BaseModel):
    """Capture settings for downstream SCQAM spectrum analyzer orchestration."""

    number_of_averages: int = Field(default=10, ge=1, description="Number of averages per channel capture.")
    resolution_bandwidth_hz: ResolutionBw = Field(
        default=ResolutionBw(25_000),
        gt=0,
        description="Resolution bandwidth in Hz.",
    )
    spectrum_retrieval_type: SpectrumRetrievalType = Field(
        default=SpectrumRetrievalType.FILE,
        description="Spectrum retrieval type.",
    )


class ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest(BaseModel):
    """Request payload for SG-level SCQAM SpectrumAnalyzer startCapture."""

    model_config = ConfigDict(extra="ignore")

    cmts: CmtsRequestEnvelopeModel = Field(default_factory=CmtsRequestEnvelopeModel, description="CMTS request envelope.")
    execution: ScQamSpectrumAnalyzerServiceGroupExecutionModel = Field(
        default_factory=ScQamSpectrumAnalyzerServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )
    capture_settings: ScQamSpectrumAnalyzerCaptureSettingsModel = Field(
        default_factory=ScQamSpectrumAnalyzerCaptureSettingsModel,
        description="SCQAM spectrum analyzer capture settings.",
    )


class ScQamSpectrumAnalyzerServiceGroupOperationRequest(BaseModel):
    """Request payload for SG-level SCQAM SpectrumAnalyzer operation lookup."""

    pnm_capture_operation_id: PnmCaptureOperationId = Field(..., description="Operation identifier.")


class ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse(BaseModel):
    """Response payload for SG-level SCQAM SpectrumAnalyzer startCapture."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel = Field(..., description="Initial operation state.")


class ScQamSpectrumAnalyzerServiceGroupStatusResponse(BaseModel):
    """Response payload for SG-level SCQAM SpectrumAnalyzer status."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Operation state snapshot.")


class ScQamSpectrumAnalyzerServiceGroupCancelResponse(BaseModel):
    """Response payload for SG-level SCQAM SpectrumAnalyzer cancel."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Updated operation state.")


class ScQamSpectrumAnalyzerServiceGroupResultsResponse(BaseModel):
    """Response payload for SG-level SCQAM SpectrumAnalyzer results."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    summary: OperationResultsSummaryModel = Field(
        default_factory=OperationResultsSummaryModel,
        description="Results summary for the operation.",
    )
    records: list[PerModemLinkageRecordModel] = Field(
        default_factory=list,
        description="Linkage records included in the response.",
    )


__all__ = [
    "ScQamSpectrumAnalyzerCaptureSettingsModel",
    "ScQamSpectrumAnalyzerServiceGroupCancelResponse",
    "ScQamSpectrumAnalyzerServiceGroupExecutionModel",
    "ScQamSpectrumAnalyzerServiceGroupOperationRequest",
    "ScQamSpectrumAnalyzerServiceGroupResultsResponse",
    "ScQamSpectrumAnalyzerServiceGroupStartCaptureRequest",
    "ScQamSpectrumAnalyzerServiceGroupStartCaptureResponse",
    "ScQamSpectrumAnalyzerServiceGroupStatusResponse",
]

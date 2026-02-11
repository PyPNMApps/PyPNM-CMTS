# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pypnm.api.routes.common.classes.analysis.analysis import WindowFunction
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.docsis.cm_snmp_operation import SpectrumRetrievalType
from pypnm.lib.types import FrequencyHz, ResolutionBw

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


class SpectrumAnalyzerServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group SpectrumAnalyzer orchestration."""

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


class SpectrumAnalyzerCaptureSettingsModel(BaseModel):
    """Capture settings for full-bandwidth spectrum analyzer orchestration."""

    inactivity_timeout: int = Field(default=60, gt=0, description="Inactivity timeout in seconds.")
    first_segment_center_freq: FrequencyHz = Field(
        default=FrequencyHz(300_000_000),
        gt=0,
        description="Requested first segment center frequency in Hz.",
    )
    last_segment_center_freq: FrequencyHz = Field(
        default=FrequencyHz(900_000_000),
        gt=0,
        description="Requested last segment center frequency in Hz.",
    )
    resolution_bw: ResolutionBw = Field(
        default=ResolutionBw(30_000),
        gt=0,
        description="Resolution bandwidth in Hz.",
    )
    noise_bw: int = Field(default=150, ge=0, description="Equivalent noise bandwidth in kHz.")
    window_function: WindowFunction = Field(
        default=WindowFunction.HANN,
        description="FFT window function.",
    )
    num_averages: int = Field(default=1, ge=1, description="Number of averages.")
    spectrum_retrieval_type: SpectrumRetrievalType = Field(
        default=SpectrumRetrievalType.FILE,
        description="Spectrum retrieval type.",
    )


class SpectrumAnalyzerServiceGroupStartCaptureRequest(BaseModel):
    """Request payload for SG-level SpectrumAnalyzer startCapture."""

    model_config = ConfigDict(extra="ignore")

    cmts: CmtsRequestEnvelopeModel = Field(default_factory=CmtsRequestEnvelopeModel, description="CMTS request envelope.")
    execution: SpectrumAnalyzerServiceGroupExecutionModel = Field(
        default_factory=SpectrumAnalyzerServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )
    capture_settings: SpectrumAnalyzerCaptureSettingsModel = Field(
        default_factory=SpectrumAnalyzerCaptureSettingsModel,
        description="Spectrum analyzer capture settings.",
    )


class SpectrumAnalyzerServiceGroupOperationRequest(BaseModel):
    """Request payload for SG-level SpectrumAnalyzer operation lookup."""

    pnm_capture_operation_id: PnmCaptureOperationId = Field(..., description="Operation identifier.")


class SpectrumAnalyzerServiceGroupStartCaptureResponse(BaseModel):
    """Response payload for SG-level SpectrumAnalyzer startCapture."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel = Field(..., description="Initial operation state.")


class SpectrumAnalyzerServiceGroupStatusResponse(BaseModel):
    """Response payload for SG-level SpectrumAnalyzer status."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Operation state snapshot.")


class SpectrumAnalyzerServiceGroupCancelResponse(BaseModel):
    """Response payload for SG-level SpectrumAnalyzer cancel."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Updated operation state.")


class SpectrumAnalyzerServiceGroupResultsResponse(BaseModel):
    """Response payload for SG-level SpectrumAnalyzer results."""

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
    "SpectrumAnalyzerServiceGroupCancelResponse",
    "SpectrumAnalyzerCaptureSettingsModel",
    "SpectrumAnalyzerServiceGroupExecutionModel",
    "SpectrumAnalyzerServiceGroupOperationRequest",
    "SpectrumAnalyzerServiceGroupResultsResponse",
    "SpectrumAnalyzerServiceGroupStartCaptureRequest",
    "SpectrumAnalyzerServiceGroupStartCaptureResponse",
    "SpectrumAnalyzerServiceGroupStatusResponse",
]

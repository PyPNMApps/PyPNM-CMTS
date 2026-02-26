# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsServingGroupFilterModel,
    CmtsSnmpModel,
    CmtsTftpParametersModel,
)
from pypnm_cmts.api.common.operations.request_schemas import (
    PnmCaptureOperationLookupRequest,
    PnmCaptureResultsRequest,
)
from pypnm_cmts.api.common.operations.response_schemas import (
    PnmCaptureOperationResponseModel,
    PnmCaptureResultsResponseModel,
    PnmCaptureStartResponseModel,
)
from pypnm_cmts.api.common.service.pnm.results_schemas import (
    PnmCableModemResultsBaseModel,
    PnmCaptureDetailsModel,
    PnmDecodedAnalysisResultModel,
    PnmResultsCmtsModel,
    PnmResultsStageMessagesModel,
    PnmResultsStageStatusCodesModel,
    PnmServingGroupGroupedResultsModel,
    PnmServingGroupWithCableModemsResultsModel,
)

DEFAULT_MAX_WORKERS = 16
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY_SECONDS = 5.0
DEFAULT_PER_MODEM_TIMEOUT_SECONDS = 30.0
DEFAULT_OVERALL_TIMEOUT_SECONDS = 120.0


class DsHistogramServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group downstream Histogram orchestration."""

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


class DsHistogramCaptureSettingsModel(BaseModel):
    """Capture settings for downstream histogram orchestration."""

    sample_duration: int = Field(default=10, gt=0, description="Histogram sample duration in seconds.")


class DsHistogramCmtsPnmParametersModel(BaseModel):
    """Histogram-specific PNM override parameters."""

    tftp: CmtsTftpParametersModel | None = Field(default=None, description="Optional TFTP override parameters.")


class DsHistogramCmtsCableModemFilterModel(CmtsCableModemFilterModel):
    """Histogram-specific cable modem filter and overrides."""

    pnm_parameters: DsHistogramCmtsPnmParametersModel | None = Field(
        default=None,
        description="Optional PNM override parameters.",
    )
    snmp: CmtsSnmpModel | None = Field(default=None, description="Optional SNMP override parameters.")


class DsHistogramCmtsRequestEnvelopeModel(BaseModel):
    """Histogram-specific CMTS request envelope."""

    serving_group: CmtsServingGroupFilterModel = Field(
        default_factory=CmtsServingGroupFilterModel,
        description="Serving group selection.",
    )
    cable_modem: DsHistogramCmtsCableModemFilterModel = Field(
        default_factory=DsHistogramCmtsCableModemFilterModel,
        description="Cable modem selection and overrides.",
    )


class DsHistogramServiceGroupStartCaptureRequest(BaseModel):
    """Request payload for SG-level downstream Histogram startCapture."""

    model_config = ConfigDict(extra="ignore")

    cmts: DsHistogramCmtsRequestEnvelopeModel = Field(
        default_factory=DsHistogramCmtsRequestEnvelopeModel,
        description="CMTS request envelope.",
    )
    execution: DsHistogramServiceGroupExecutionModel = Field(
        default_factory=DsHistogramServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )
    capture_settings: DsHistogramCaptureSettingsModel = Field(
        default_factory=DsHistogramCaptureSettingsModel,
        description="Downstream histogram capture settings.",
    )


class DsHistogramServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level downstream Histogram operation lookup."""


class DsHistogramServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level downstream Histogram results lookup and rendering."""


class DsHistogramServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level downstream Histogram startCapture."""


class DsHistogramServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level downstream Histogram status."""


class DsHistogramServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level downstream Histogram cancel."""


class DsHistogramCaptureDetailsModel(PnmCaptureDetailsModel):
    """Histogram capture metadata."""

    capture_type: str = Field(default="HISTOGRAM", description="Capture type identifier.")


class DsHistogramResultsCmtsModel(PnmResultsCmtsModel):
    """Histogram CMTS context."""


class DsHistogramResultsDataModel(PnmDecodedAnalysisResultModel):
    """Histogram modem data payload backed by linkage + decoded analysis."""

    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class DsHistogramResultsCableModemModel(PnmCableModemResultsBaseModel):
    """Histogram cable modem result."""

    histogram_data: DsHistogramResultsDataModel = Field(
        default_factory=DsHistogramResultsDataModel,
        description="Histogram modem data payload.",
    )


class DsHistogramResultsServingGroupModel(PnmServingGroupWithCableModemsResultsModel[DsHistogramResultsCableModemModel]):
    """Serving-group grouped histogram results."""


class DsHistogramServiceGroupResultsModel(
    PnmServingGroupGroupedResultsModel[
        DsHistogramCaptureDetailsModel,
        DsHistogramResultsCmtsModel,
        DsHistogramResultsServingGroupModel,
    ]
):
    """Structured downstream Histogram results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = DsHistogramCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = DsHistogramResultsCmtsModel


class DsHistogramServiceGroupResultsResponse(PnmCaptureResultsResponseModel[DsHistogramServiceGroupResultsModel]):
    """Response payload for SG-level downstream Histogram results."""

    _results_factory: ClassVar[type[BaseModel]] = DsHistogramServiceGroupResultsModel


__all__ = [
    "DsHistogramCaptureSettingsModel",
    "DsHistogramCmtsCableModemFilterModel",
    "DsHistogramCmtsPnmParametersModel",
    "DsHistogramCmtsRequestEnvelopeModel",
    "DsHistogramResultsCableModemModel",
    "DsHistogramResultsDataModel",
    "DsHistogramResultsServingGroupModel",
    "DsHistogramServiceGroupCancelResponse",
    "DsHistogramServiceGroupExecutionModel",
    "DsHistogramServiceGroupOperationRequest",
    "DsHistogramServiceGroupResultsModel",
    "DsHistogramServiceGroupResultsRequest",
    "DsHistogramServiceGroupResultsResponse",
    "DsHistogramServiceGroupStartCaptureRequest",
    "DsHistogramServiceGroupStartCaptureResponse",
    "DsHistogramServiceGroupStatusResponse",
]

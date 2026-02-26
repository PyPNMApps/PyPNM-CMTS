# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field
from pypnm.docsis.cm_snmp_operation import FecSummaryType

from pypnm_cmts.api.common.operations.request_schemas import (
    PnmCaptureOperationLookupRequest,
    PnmCaptureResultsRequest,
    PnmCmtsRequestEnvelopeRequest,
)
from pypnm_cmts.api.common.operations.response_schemas import (
    PnmCaptureOperationResponseModel,
    PnmCaptureResultsResponseModel,
    PnmCaptureStartResponseModel,
)
from pypnm_cmts.api.common.service.pnm.results_schemas import (
    PnmCableModemResultsBaseModel,
    PnmCaptureDetailsModel,
    PnmChannelGroupedResultsModel,
    PnmChannelWithCableModemsResultsModel,
    PnmDecodedAnalysisResultModel,
    PnmResultsCmtsModel,
    PnmResultsStageMessagesModel,
    PnmResultsStageStatusCodesModel,
    PnmServingGroupWithChannelsResultsModel,
)

DEFAULT_MAX_WORKERS = 16
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY_SECONDS = 5.0
DEFAULT_PER_MODEM_TIMEOUT_SECONDS = 30.0
DEFAULT_OVERALL_TIMEOUT_SECONDS = 120.0


class FecSummaryServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group FecSummary orchestration."""

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


class FecSummaryCaptureSettingsModel(BaseModel):
    """Capture settings for SG-level downstream OFDM FEC summary orchestration."""

    fec_summary_type: FecSummaryType = Field(
        default=FecSummaryType.TEN_MIN,
        description="FEC summary interval type (10 min = 2, 24 hr = 3).",
    )


class FecSummaryServiceGroupStartCaptureRequest(PnmCmtsRequestEnvelopeRequest):
    """Request payload for SG-level FecSummary startCapture."""

    model_config = ConfigDict(extra="ignore")

    execution: FecSummaryServiceGroupExecutionModel = Field(
        default_factory=FecSummaryServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )
    capture_settings: FecSummaryCaptureSettingsModel = Field(
        default_factory=FecSummaryCaptureSettingsModel,
        description="FEC summary capture settings.",
    )


class FecSummaryServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level FecSummary operation lookup."""


class FecSummaryServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level FecSummary results lookup and rendering."""


class FecSummaryServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level FecSummary startCapture."""


class FecSummaryServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level FecSummary status."""


class FecSummaryServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level FecSummary cancel."""


class FecSummaryCaptureDetailsModel(PnmCaptureDetailsModel):
    """FecSummary capture metadata."""

    capture_type: str = Field(default="FEC_SUMMARY", description="Capture type identifier.")


class FecSummaryResultsCmtsModel(PnmResultsCmtsModel):
    """FecSummary CMTS context."""


class FecSummaryResultsDataModel(PnmDecodedAnalysisResultModel):
    """FecSummary modem data payload backed by linkage + decoded analysis."""

    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class FecSummaryResultsCableModemModel(PnmCableModemResultsBaseModel):
    """FecSummary cable modem result."""

    fec_summary_data: FecSummaryResultsDataModel = Field(
        default_factory=FecSummaryResultsDataModel,
        description="FecSummary modem data payload.",
    )


class FecSummaryResultsChannelModel(PnmChannelWithCableModemsResultsModel[FecSummaryResultsCableModemModel]):
    """FecSummary channel group."""


class FecSummaryResultsServingGroupModel(PnmServingGroupWithChannelsResultsModel[FecSummaryResultsChannelModel]):
    """Serving-group grouped FecSummary results."""


class FecSummaryServiceGroupResultsModel(
    PnmChannelGroupedResultsModel[FecSummaryCaptureDetailsModel, FecSummaryResultsCmtsModel, FecSummaryResultsChannelModel]
):
    """Structured FecSummary results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = FecSummaryCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = FecSummaryResultsCmtsModel
    serving_groups: list[FecSummaryResultsServingGroupModel] = Field(
        default_factory=list,
        description="Serving-group grouped FecSummary results.",
    )


class FecSummaryServiceGroupResultsResponse(PnmCaptureResultsResponseModel[FecSummaryServiceGroupResultsModel]):
    """Response payload for SG-level FecSummary results."""

    _results_factory: ClassVar[type[BaseModel]] = FecSummaryServiceGroupResultsModel


__all__ = [
    "FecSummaryCaptureSettingsModel",
    "FecSummaryResultsCableModemModel",
    "FecSummaryResultsChannelModel",
    "FecSummaryResultsDataModel",
    "FecSummaryResultsServingGroupModel",
    "FecSummaryServiceGroupCancelResponse",
    "FecSummaryServiceGroupExecutionModel",
    "FecSummaryServiceGroupOperationRequest",
    "FecSummaryServiceGroupResultsModel",
    "FecSummaryServiceGroupResultsRequest",
    "FecSummaryServiceGroupResultsResponse",
    "FecSummaryServiceGroupStartCaptureRequest",
    "FecSummaryServiceGroupStartCaptureResponse",
    "FecSummaryServiceGroupStatusResponse",
]

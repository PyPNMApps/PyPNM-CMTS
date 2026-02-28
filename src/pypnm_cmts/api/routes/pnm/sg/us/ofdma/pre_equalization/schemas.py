# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

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


class PreEqualizationServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group PreEqualization orchestration."""

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


class PreEqualizationServiceGroupStartCaptureRequest(PnmCmtsRequestEnvelopeRequest):
    """Request payload for SG-level PreEqualization startCapture."""

    model_config = ConfigDict(extra="ignore")

    execution: PreEqualizationServiceGroupExecutionModel = Field(
        default_factory=PreEqualizationServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )


class PreEqualizationServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level PreEqualization operation lookup."""


class PreEqualizationServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level PreEqualization results lookup and rendering."""

class PreEqualizationServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level PreEqualization startCapture."""


class PreEqualizationServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level PreEqualization status."""


class PreEqualizationServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level PreEqualization cancel."""


class PreEqualizationCaptureDetailsModel(PnmCaptureDetailsModel):
    """PreEqualization capture metadata."""

    capture_type: str = Field(default="PRE_EQUALIZATION", description="Capture type identifier.")


class PreEqualizationResultsCmtsModel(PnmResultsCmtsModel):
    """PreEqualization CMTS context."""


class PreEqualizationResultsDataModel(PnmDecodedAnalysisResultModel):
    """PreEqualization modem data payload backed by linkage and decoded analysis."""

    channel_estimate_magnitude_db: list[float] | None = Field(
        default=None,
        description="Per-subcarrier pre-equalization channel-estimate magnitude in dB when provided by analysis.",
    )
    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class PreEqualizationResultsCableModemModel(PnmCableModemResultsBaseModel):
    """PreEqualization cable modem result."""

    pre_equalization_data: PreEqualizationResultsDataModel = Field(
        default_factory=PreEqualizationResultsDataModel,
        description="PreEqualization modem data payload.",
    )


class PreEqualizationResultsChannelModel(PnmChannelWithCableModemsResultsModel[PreEqualizationResultsCableModemModel]):
    """Channel-grouped pre-equalization results."""


class PreEqualizationResultsServingGroupModel(
    PnmServingGroupWithChannelsResultsModel[PreEqualizationResultsChannelModel]
):
    """Serving-group grouped pre-equalization results."""


class PreEqualizationServiceGroupResultsModel(
    PnmChannelGroupedResultsModel[
        PreEqualizationCaptureDetailsModel,
        PreEqualizationResultsCmtsModel,
        PreEqualizationResultsChannelModel,
    ]
):
    """Structured pre-equalization results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = PreEqualizationCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = PreEqualizationResultsCmtsModel
    serving_groups: list[PreEqualizationResultsServingGroupModel] = Field(
        default_factory=list,
        description="Serving-group grouped pre-equalization results.",
    )


class PreEqualizationServiceGroupResultsResponse(PnmCaptureResultsResponseModel[PreEqualizationServiceGroupResultsModel]):
    """Response payload for SG-level PreEqualization results."""

    _results_factory: ClassVar[type[BaseModel]] = PreEqualizationServiceGroupResultsModel


__all__ = [
    "PreEqualizationResultsCableModemModel",
    "PreEqualizationResultsChannelModel",
    "PreEqualizationResultsDataModel",
    "PreEqualizationResultsServingGroupModel",
    "PreEqualizationServiceGroupCancelResponse",
    "PreEqualizationServiceGroupExecutionModel",
    "PreEqualizationServiceGroupOperationRequest",
    "PreEqualizationServiceGroupResultsModel",
    "PreEqualizationServiceGroupResultsRequest",
    "PreEqualizationServiceGroupResultsResponse",
    "PreEqualizationServiceGroupStartCaptureRequest",
    "PreEqualizationServiceGroupStartCaptureResponse",
    "PreEqualizationServiceGroupStatusResponse",
]

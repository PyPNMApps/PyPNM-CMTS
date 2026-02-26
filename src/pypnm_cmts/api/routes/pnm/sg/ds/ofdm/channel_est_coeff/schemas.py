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


class ChannelEstCoeffServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group ChannelEstCoeff orchestration."""

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


class ChannelEstCoeffServiceGroupStartCaptureRequest(PnmCmtsRequestEnvelopeRequest):
    """Request payload for SG-level ChannelEstCoeff startCapture."""

    model_config = ConfigDict(extra="ignore")

    execution: ChannelEstCoeffServiceGroupExecutionModel = Field(
        default_factory=ChannelEstCoeffServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )


class ChannelEstCoeffServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level ChannelEstCoeff operation lookup."""


class ChannelEstCoeffServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level ChannelEstCoeff results lookup and rendering."""


class ChannelEstCoeffServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level ChannelEstCoeff startCapture."""


class ChannelEstCoeffServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level ChannelEstCoeff status."""


class ChannelEstCoeffServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level ChannelEstCoeff cancel."""


class ChannelEstCoeffCaptureDetailsModel(PnmCaptureDetailsModel):
    """ChannelEstCoeff capture metadata."""

    capture_type: str = Field(default="CHANNEL_EST_COEFF", description="Capture type identifier.")


class ChannelEstCoeffResultsCmtsModel(PnmResultsCmtsModel):
    """ChannelEstCoeff CMTS context."""


class ChannelEstCoeffResultsDataModel(PnmDecodedAnalysisResultModel):
    """ChannelEstCoeff modem data payload backed by linkage + decoded analysis."""

    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class ChannelEstCoeffResultsCableModemModel(PnmCableModemResultsBaseModel):
    """ChannelEstCoeff cable modem result."""

    channel_est_coeff_data: ChannelEstCoeffResultsDataModel = Field(
        default_factory=ChannelEstCoeffResultsDataModel,
        description="ChannelEstCoeff modem data payload.",
    )


class ChannelEstCoeffResultsChannelModel(PnmChannelWithCableModemsResultsModel[ChannelEstCoeffResultsCableModemModel]):
    """ChannelEstCoeff channel group."""


class ChannelEstCoeffResultsServingGroupModel(
    PnmServingGroupWithChannelsResultsModel[ChannelEstCoeffResultsChannelModel]
):
    """Serving-group grouped ChannelEstCoeff results."""


class ChannelEstCoeffServiceGroupResultsModel(
    PnmChannelGroupedResultsModel[
        ChannelEstCoeffCaptureDetailsModel,
        ChannelEstCoeffResultsCmtsModel,
        ChannelEstCoeffResultsChannelModel,
    ]
):
    """Structured ChannelEstCoeff results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = ChannelEstCoeffCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = ChannelEstCoeffResultsCmtsModel
    serving_groups: list[ChannelEstCoeffResultsServingGroupModel] = Field(
        default_factory=list,
        description="Serving-group grouped ChannelEstCoeff results.",
    )


class ChannelEstCoeffServiceGroupResultsResponse(PnmCaptureResultsResponseModel[ChannelEstCoeffServiceGroupResultsModel]):
    """Response payload for SG-level ChannelEstCoeff results."""

    _results_factory: ClassVar[type[BaseModel]] = ChannelEstCoeffServiceGroupResultsModel


__all__ = [
    "ChannelEstCoeffResultsCableModemModel",
    "ChannelEstCoeffResultsChannelModel",
    "ChannelEstCoeffResultsDataModel",
    "ChannelEstCoeffResultsServingGroupModel",
    "ChannelEstCoeffServiceGroupCancelResponse",
    "ChannelEstCoeffServiceGroupExecutionModel",
    "ChannelEstCoeffServiceGroupOperationRequest",
    "ChannelEstCoeffServiceGroupResultsModel",
    "ChannelEstCoeffServiceGroupResultsRequest",
    "ChannelEstCoeffServiceGroupResultsResponse",
    "ChannelEstCoeffServiceGroupStartCaptureRequest",
    "ChannelEstCoeffServiceGroupStartCaptureResponse",
    "ChannelEstCoeffServiceGroupStatusResponse",
]

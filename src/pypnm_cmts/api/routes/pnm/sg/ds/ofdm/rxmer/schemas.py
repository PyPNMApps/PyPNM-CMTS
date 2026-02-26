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


class RxMerServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group RxMER orchestration."""

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


class RxMerServiceGroupStartCaptureRequest(PnmCmtsRequestEnvelopeRequest):
    """Request payload for SG-level RxMER startCapture."""

    model_config = ConfigDict(extra="ignore")

    execution: RxMerServiceGroupExecutionModel = Field(
        default_factory=RxMerServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )


class RxMerServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level RxMER operation lookup."""
    pass


class RxMerServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level RxMER results lookup and rendering."""
    pass


class RxMerServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level RxMER startCapture."""


class RxMerServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level RxMER status."""


class RxMerServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level RxMER cancel."""


class RxMerCaptureDetailsModel(PnmCaptureDetailsModel):
    """RxMER capture metadata."""

    capture_type: str = Field(default="RXMER", description="Capture type identifier.")


class RxMerResultsCmtsModel(PnmResultsCmtsModel):
    """RxMER CMTS context."""


class RxMerResultsDataModel(PnmDecodedAnalysisResultModel):
    """RxMER modem data payload placeholder backed by current linkage records."""
    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class RxMerResultsCableModemModel(PnmCableModemResultsBaseModel):
    """RxMER cable modem result."""

    rxmer_data: RxMerResultsDataModel = Field(default_factory=RxMerResultsDataModel, description="RxMER modem data payload.")


class RxMerResultsChannelModel(PnmChannelWithCableModemsResultsModel[RxMerResultsCableModemModel]):
    """RxMER channel group."""


class RxMerResultsServingGroupModel(PnmServingGroupWithChannelsResultsModel[RxMerResultsChannelModel]):
    """Serving-group grouped RxMER results."""


class RxMerServiceGroupResultsModel(
    PnmChannelGroupedResultsModel[RxMerCaptureDetailsModel, RxMerResultsCmtsModel, RxMerResultsChannelModel]
):
    """Structured RxMER results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = RxMerCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = RxMerResultsCmtsModel
    serving_groups: list[RxMerResultsServingGroupModel] = Field(
        default_factory=list,
        description="Serving-group grouped RxMER results.",
    )


class RxMerServiceGroupResultsResponse(PnmCaptureResultsResponseModel[RxMerServiceGroupResultsModel]):
    """Response payload for SG-level RxMER results."""

    _results_factory: ClassVar[type[BaseModel]] = RxMerServiceGroupResultsModel


__all__ = [
    "RxMerServiceGroupCancelResponse",
    "RxMerServiceGroupExecutionModel",
    "RxMerServiceGroupOperationRequest",
    "RxMerServiceGroupResultsRequest",
    "RxMerResultsDataModel",
    "RxMerServiceGroupResultsModel",
    "RxMerServiceGroupResultsResponse",
    "RxMerServiceGroupStartCaptureRequest",
    "RxMerServiceGroupStartCaptureResponse",
    "RxMerServiceGroupStatusResponse",
]

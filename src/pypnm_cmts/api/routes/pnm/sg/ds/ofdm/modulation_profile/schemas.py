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


class ModulationProfileServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group ModulationProfile orchestration."""

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


class ModulationProfileServiceGroupStartCaptureRequest(PnmCmtsRequestEnvelopeRequest):
    """Request payload for SG-level ModulationProfile startCapture."""

    model_config = ConfigDict(extra="ignore")

    execution: ModulationProfileServiceGroupExecutionModel = Field(
        default_factory=ModulationProfileServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )


class ModulationProfileServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level ModulationProfile operation lookup."""


class ModulationProfileServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level ModulationProfile results lookup and rendering."""


class ModulationProfileServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level ModulationProfile startCapture."""


class ModulationProfileServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level ModulationProfile status."""


class ModulationProfileServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level ModulationProfile cancel."""


class ModulationProfileCaptureDetailsModel(PnmCaptureDetailsModel):
    """ModulationProfile capture metadata."""

    capture_type: str = Field(default="MODULATION_PROFILE", description="Capture type identifier.")


class ModulationProfileResultsCmtsModel(PnmResultsCmtsModel):
    """ModulationProfile CMTS context."""


class ModulationProfileResultsDataModel(PnmDecodedAnalysisResultModel):
    """ModulationProfile modem data payload backed by linkage + decoded analysis."""

    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class ModulationProfileResultsCableModemModel(PnmCableModemResultsBaseModel):
    """ModulationProfile cable modem result."""

    modulation_profile_data: ModulationProfileResultsDataModel = Field(
        default_factory=ModulationProfileResultsDataModel,
        description="ModulationProfile modem data payload.",
    )


class ModulationProfileResultsChannelModel(
    PnmChannelWithCableModemsResultsModel[ModulationProfileResultsCableModemModel]
):
    """ModulationProfile channel group."""


class ModulationProfileResultsServingGroupModel(
    PnmServingGroupWithChannelsResultsModel[ModulationProfileResultsChannelModel]
):
    """Serving-group grouped ModulationProfile results."""


class ModulationProfileServiceGroupResultsModel(
    PnmChannelGroupedResultsModel[
        ModulationProfileCaptureDetailsModel,
        ModulationProfileResultsCmtsModel,
        ModulationProfileResultsChannelModel,
    ]
):
    """Structured ModulationProfile results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = ModulationProfileCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = ModulationProfileResultsCmtsModel
    serving_groups: list[ModulationProfileResultsServingGroupModel] = Field(
        default_factory=list,
        description="Serving-group grouped ModulationProfile results.",
    )


class ModulationProfileServiceGroupResultsResponse(
    PnmCaptureResultsResponseModel[ModulationProfileServiceGroupResultsModel]
):
    """Response payload for SG-level ModulationProfile results."""

    _results_factory: ClassVar[type[BaseModel]] = ModulationProfileServiceGroupResultsModel


__all__ = [
    "ModulationProfileResultsCableModemModel",
    "ModulationProfileResultsChannelModel",
    "ModulationProfileResultsDataModel",
    "ModulationProfileResultsServingGroupModel",
    "ModulationProfileServiceGroupCancelResponse",
    "ModulationProfileServiceGroupExecutionModel",
    "ModulationProfileServiceGroupOperationRequest",
    "ModulationProfileServiceGroupResultsModel",
    "ModulationProfileServiceGroupResultsRequest",
    "ModulationProfileServiceGroupResultsResponse",
    "ModulationProfileServiceGroupStartCaptureRequest",
    "ModulationProfileServiceGroupStartCaptureResponse",
    "ModulationProfileServiceGroupStatusResponse",
]

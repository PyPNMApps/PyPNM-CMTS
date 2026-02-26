# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field
from pypnm.docsis.data_type.DsCmConstDisplay import (
    CmDsConstellationDisplayConst as ConstDisplayConstant,
)

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


class ConstDisplayServiceGroupExecutionModel(BaseModel):
    """Execution controls for serving-group ConstDisplay orchestration."""

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


class ConstellationDisplaySettingsModel(BaseModel):
    """Capture settings for downstream OFDM constellation display."""

    modulation_order_offset: int = Field(
        default=ConstDisplayConstant.MODULATION_OFFSET.value,
        description="Modulation-order offset override for constellation display capture.",
    )
    number_sample_symbol: int = Field(
        default=ConstDisplayConstant.NUM_SAMPLE_SYMBOL.value,
        description="Number of symbols to sample during constellation display capture.",
    )


class ConstDisplayServiceGroupStartCaptureRequest(PnmCmtsRequestEnvelopeRequest):
    """Request payload for SG-level ConstDisplay startCapture."""

    model_config = ConfigDict(extra="ignore")

    execution: ConstDisplayServiceGroupExecutionModel = Field(
        default_factory=ConstDisplayServiceGroupExecutionModel,
        description="Execution settings for the orchestration.",
    )
    capture_settings: ConstellationDisplaySettingsModel = Field(
        default_factory=ConstellationDisplaySettingsModel,
        description="Constellation display capture settings.",
    )


class ConstDisplayServiceGroupOperationRequest(PnmCaptureOperationLookupRequest):
    """Request payload for SG-level ConstDisplay operation lookup."""


class ConstDisplayServiceGroupResultsRequest(PnmCaptureResultsRequest):
    """Request payload for SG-level ConstDisplay results lookup and rendering."""


class ConstDisplayServiceGroupStartCaptureResponse(PnmCaptureStartResponseModel):
    """Response payload for SG-level ConstDisplay startCapture."""


class ConstDisplayServiceGroupStatusResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level ConstDisplay status."""


class ConstDisplayServiceGroupCancelResponse(PnmCaptureOperationResponseModel):
    """Response payload for SG-level ConstDisplay cancel."""


class ConstDisplayCaptureDetailsModel(PnmCaptureDetailsModel):
    """ConstDisplay capture metadata."""

    capture_type: str = Field(default="CONSTELLATION_DISPLAY", description="Capture type identifier.")


class ConstDisplayResultsCmtsModel(PnmResultsCmtsModel):
    """ConstDisplay CMTS context."""


class ConstDisplayResultsDataModel(PnmDecodedAnalysisResultModel):
    """ConstDisplay modem data payload backed by linkage + decoded analysis."""

    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class ConstDisplayResultsCableModemModel(PnmCableModemResultsBaseModel):
    """ConstDisplay cable modem result."""

    constellation_display_data: ConstDisplayResultsDataModel = Field(
        default_factory=ConstDisplayResultsDataModel,
        description="ConstellationDisplay modem data payload.",
    )


class ConstDisplayResultsChannelModel(PnmChannelWithCableModemsResultsModel[ConstDisplayResultsCableModemModel]):
    """ConstDisplay channel group."""


class ConstDisplayResultsServingGroupModel(PnmServingGroupWithChannelsResultsModel[ConstDisplayResultsChannelModel]):
    """Serving-group grouped ConstDisplay results."""


class ConstDisplayServiceGroupResultsModel(
    PnmChannelGroupedResultsModel[ConstDisplayCaptureDetailsModel, ConstDisplayResultsCmtsModel, ConstDisplayResultsChannelModel]
):
    """Structured ConstDisplay results payload for UI/API consumers."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = ConstDisplayCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = ConstDisplayResultsCmtsModel
    serving_groups: list[ConstDisplayResultsServingGroupModel] = Field(
        default_factory=list,
        description="Serving-group grouped ConstDisplay results.",
    )


class ConstDisplayServiceGroupResultsResponse(PnmCaptureResultsResponseModel[ConstDisplayServiceGroupResultsModel]):
    """Response payload for SG-level ConstDisplay results."""

    _results_factory: ClassVar[type[BaseModel]] = ConstDisplayServiceGroupResultsModel


__all__ = [
    "ConstellationDisplaySettingsModel",
    "ConstDisplayResultsCableModemModel",
    "ConstDisplayResultsChannelModel",
    "ConstDisplayResultsDataModel",
    "ConstDisplayResultsServingGroupModel",
    "ConstDisplayServiceGroupCancelResponse",
    "ConstDisplayServiceGroupExecutionModel",
    "ConstDisplayServiceGroupOperationRequest",
    "ConstDisplayServiceGroupResultsModel",
    "ConstDisplayServiceGroupResultsRequest",
    "ConstDisplayServiceGroupResultsResponse",
    "ConstDisplayServiceGroupStartCaptureRequest",
    "ConstDisplayServiceGroupStartCaptureResponse",
    "ConstDisplayServiceGroupStatusResponse",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import (
    ChannelId,
    FileNameStr,
    MacAddressStr,
    TimestampSec,
    TransactionId,
)

from pypnm_cmts.lib.constants import PnmCaptureStatus
from pypnm_cmts.lib.types import ServiceGroupId

PnmCaptureDetailsModelT = TypeVar("PnmCaptureDetailsModelT", bound="PnmCaptureDetailsModel")
PnmResultsCmtsModelT = TypeVar("PnmResultsCmtsModelT", bound="PnmResultsCmtsModel")
PnmCableModemResultsModelT = TypeVar("PnmCableModemResultsModelT", bound=BaseModel)
PnmChannelResultsModelT = TypeVar("PnmChannelResultsModelT", bound=BaseModel)
PnmServingGroupResultsModelT = TypeVar("PnmServingGroupResultsModelT", bound=BaseModel)


class PnmCaptureDetailsModel(BaseModel):
    """Shared capture metadata for structured PNM results payloads."""

    capture_type: str = Field(default="", description="Capture type identifier.")
    capture_time_epoch: TimestampSec | None = Field(default=None, description="Capture completion time in epoch seconds.")


class PnmResultsCmtsModel(BaseModel):
    """Shared CMTS context for structured PNM results payloads."""

    cmts_hostname: str | None = Field(default=None, description="CMTS hostname if available.")


class PnmChannelResultsBaseModel(BaseModel):
    """Shared channel grouping fields for structured PNM results payloads."""

    channel_id: ChannelId | None = Field(default=None, description="Channel identifier if available.")
    service_group_id: ServiceGroupId | None = Field(default=None, description="Serving group identifier if available.")


class PnmCableModemResultsBaseModel(BaseModel):
    """Shared per-modem fields for structured PNM results payloads."""

    mac_address: MacAddressStr | None = Field(default=None, description="Cable modem MAC address.")
    system_description: dict[str, str] | None = Field(default=None, description="Parsed modem system description fields.")
    status: PnmCaptureStatus = Field(default=PnmCaptureStatus.FAILED, description="Final modem capture status.")
    message: str = Field(default="", description="Final modem capture status message.")


class PnmChannelWithCableModemsResultsModel(BaseModel, Generic[PnmCableModemResultsModelT]):
    """Shared channel-grouped modem container for structured PNM results payloads."""

    channel_id: ChannelId | None = Field(default=None, description="Channel identifier if available.")
    service_group_id: ServiceGroupId | None = Field(default=None, description="Serving group identifier if available.")
    cable_modems: list[PnmCableModemResultsModelT] = Field(default_factory=list, description="Per-modem results.")


class PnmServingGroupWithChannelsResultsModel(BaseModel, Generic[PnmChannelResultsModelT]):
    """Shared serving-group container for channel-grouped structured PNM results payloads."""

    service_group_id: ServiceGroupId | None = Field(default=None, description="Serving group identifier for this group.")
    channels: list[PnmChannelResultsModelT] = Field(default_factory=list, description="Channel-grouped results.")


class PnmResultsStageStatusCodesModel(BaseModel):
    """Per-stage status-code summary shared across PNM operation results."""

    eligibility: ServiceStatusCode | None = Field(default=None, description="Eligibility stage status code.")
    precheck: ServiceStatusCode | None = Field(default=None, description="Precheck stage status code.")
    capture: ServiceStatusCode | None = Field(default=None, description="Capture stage status code.")


class PnmResultsStageMessagesModel(BaseModel):
    """Per-stage messages shared across PNM operation results."""

    eligibility: str | None = Field(default=None, description="Eligibility stage message.")
    precheck: str | None = Field(default=None, description="Precheck stage message.")
    capture: str | None = Field(default=None, description="Capture stage message.")


class PnmAnalyzedFileLinkModel(BaseModel):
    """Normalized single analyzed file reference shared across PNM results payloads."""

    transaction_id: str | None = Field(default=None, description="Transaction identifier for the analyzed PNM file.")
    filename: str | None = Field(default=None, description="Filename for the analyzed PNM file.")


class PnmAnalyzedFileResultModel(BaseModel):
    """Shared single analyzed-file field for structured PNM modem data payloads."""

    file: PnmAnalyzedFileLinkModel | None = Field(default=None, description="Normalized analyzed file reference.")


class PnmResultsLinkageDataModel(BaseModel):
    """Generic linkage-backed analysis placeholder shared across PNM operation results."""

    transaction_ids: list[TransactionId] = Field(default_factory=list, description="Capture transaction identifiers.")
    filenames: list[FileNameStr] = Field(default_factory=list, description="Capture filenames.")
    stage_status_codes: PnmResultsStageStatusCodesModel = Field(
        default_factory=PnmResultsStageStatusCodesModel,
        description="Stage status summary.",
    )
    stage_messages: PnmResultsStageMessagesModel | None = Field(
        default=None,
        description="Optional per-stage messages.",
    )


class PnmDecodedAnalysisResultModel(PnmAnalyzedFileResultModel):
    """Shared decoded-analysis fields for structured PNM modem data payloads."""

    pnm_file_type: str | None = Field(default=None, description="Resolved PNM file type for the decoded analysis.")
    analysis: dict[str, object] | None = Field(default=None, description="Decoded basic analysis payload.")
    analysis_error: str | None = Field(default=None, description="Decode/analysis error when analysis could not be produced.")


class PnmChannelGroupedResultsModel(
    BaseModel,
    Generic[PnmCaptureDetailsModelT, PnmResultsCmtsModelT, PnmChannelResultsModelT],
):
    """Generic channel-grouped structured results payload for PNM operations."""

    _capture_details_factory: ClassVar[type[PnmCaptureDetailsModel]] = PnmCaptureDetailsModel
    _cmts_factory: ClassVar[type[PnmResultsCmtsModel]] = PnmResultsCmtsModel

    capture_details: PnmCaptureDetailsModelT = Field(default_factory=PnmCaptureDetailsModel, description="Capture metadata.")
    cmts: PnmResultsCmtsModelT = Field(default_factory=PnmResultsCmtsModel, description="CMTS metadata.")
    channels: list[PnmChannelResultsModelT] = Field(default_factory=list, description="Channel-grouped results.")

    @model_validator(mode="before")
    @classmethod
    def _apply_default_grouping_models(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        normalized.setdefault("capture_details", cls._capture_details_factory())
        normalized.setdefault("cmts", cls._cmts_factory())
        return normalized


__all__ = [
    "PnmAnalyzedFileLinkModel",
    "PnmAnalyzedFileResultModel",
    "PnmCableModemResultsBaseModel",
    "PnmChannelWithCableModemsResultsModel",
    "PnmChannelGroupedResultsModel",
    "PnmCaptureDetailsModel",
    "PnmChannelResultsBaseModel",
    "PnmResultsLinkageDataModel",
    "PnmResultsCmtsModel",
    "PnmDecodedAnalysisResultModel",
    "PnmResultsStageMessagesModel",
    "PnmResultsStageStatusCodesModel",
    "PnmServingGroupWithChannelsResultsModel",
]

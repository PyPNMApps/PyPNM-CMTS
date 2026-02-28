# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from pypnm.api.routes.common.classes.common_endpoint_classes.common.enum import (
    AnalysisType,
    OutputType,
)
from pypnm.lib.types import ChannelId, MacAddressStr

from pypnm_cmts.api.common.cmts_request import CmtsRequestEnvelopeModel
from pypnm_cmts.lib.types import PnmCaptureOperationId, ServiceGroupId


class PnmCaptureOperationLookupRequest(BaseModel):
    """Nested lookup model for filesystem-backed PNM capture operations."""

    pnm_capture_operation_id: PnmCaptureOperationId = Field(..., description="Operation identifier.")


class PnmCmtsRequestEnvelopeRequest(BaseModel):
    """Shared CMTS request-envelope field for PNM CMTS endpoints."""

    cmts: CmtsRequestEnvelopeModel = Field(default_factory=CmtsRequestEnvelopeModel, description="CMTS request envelope.")


class PnmCaptureSelectionRequest(BaseModel):
    """Generic post-capture selection filters for PNM operation results."""

    serving_group_ids: list[ServiceGroupId] = Field(default_factory=list, description="Serving group filters (empty means all).")
    channel_ids: list[ChannelId] = Field(default_factory=list, description="Channel filters (empty means all).")
    mac_addresses: list[MacAddressStr] = Field(default_factory=list, description="MAC filters (empty means all).")


class PnmResultsArchiveIncludesRequest(BaseModel):
    """Generic archive include flags for PNM results endpoints."""

    pnm_files: bool = Field(default=True, description="Include raw PNM capture files.")
    png: bool = Field(default=False, description="Include generated PNG plots.")
    json_output: bool = Field(default=True, alias="json", description="Include JSON analysis payload.")


class PnmResultsOutputRequest(BaseModel):
    """Generic output controls for PNM results endpoints."""

    type: OutputType = Field(default=OutputType.JSON, description="Output type control: json or archive.")
    archive_includes: PnmResultsArchiveIncludesRequest | None = Field(
        default=None,
        description="Archive content selection (valid only when output.type=archive).",
    )

    @model_validator(mode="after")
    def _validate_archive_includes(self) -> PnmResultsOutputRequest:
        if self.type != OutputType.ARCHIVE:
            self.archive_includes = None
        return self


class PnmResultsAnalysisRequest(BaseModel):
    """Generic analysis controls for PNM results endpoints."""

    type: AnalysisType = Field(default=AnalysisType.BASIC, description="Analysis type to perform.")


class PnmCaptureResultsRequest(BaseModel):
    """Generic request payload for PNM results endpoints."""

    operation: PnmCaptureOperationLookupRequest = Field(..., description="Operation lookup.")
    selection: PnmCaptureSelectionRequest = Field(
        default_factory=PnmCaptureSelectionRequest,
        description="Optional result filters.",
    )
    analysis: PnmResultsAnalysisRequest = Field(
        default_factory=PnmResultsAnalysisRequest,
        description="Analysis controls.",
    )
    output: PnmResultsOutputRequest = Field(
        default_factory=PnmResultsOutputRequest,
        description="Output controls.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_flat_request(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "operation" in data:
            return data
        operation_id = data.get("pnm_capture_operation_id")
        if operation_id is None:
            return data
        payload = dict(data)
        payload.pop("pnm_capture_operation_id", None)
        payload["operation"] = {"pnm_capture_operation_id": operation_id}
        return payload


__all__ = [
    "PnmCmtsRequestEnvelopeRequest",
    "PnmCaptureResultsRequest",
    "PnmCaptureSelectionRequest",
    "PnmCaptureOperationLookupRequest",
    "PnmResultsArchiveIncludesRequest",
    "PnmResultsAnalysisRequest",
    "PnmResultsOutputRequest",
]

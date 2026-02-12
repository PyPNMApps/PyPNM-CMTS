# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsServingGroupFilterModel,
    CmtsSnmpModel,
    CmtsTftpParametersModel,
)
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


class DsHistogramServiceGroupOperationRequest(BaseModel):
    """Request payload for SG-level downstream Histogram operation lookup."""

    pnm_capture_operation_id: PnmCaptureOperationId = Field(..., description="Operation identifier.")


class DsHistogramServiceGroupStartCaptureResponse(BaseModel):
    """Response payload for SG-level downstream Histogram startCapture."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel = Field(..., description="Initial operation state.")


class DsHistogramServiceGroupStatusResponse(BaseModel):
    """Response payload for SG-level downstream Histogram status."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Operation state snapshot.")


class DsHistogramServiceGroupCancelResponse(BaseModel):
    """Response payload for SG-level downstream Histogram cancel."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Updated operation state.")


class DsHistogramServiceGroupResultsResponse(BaseModel):
    """Response payload for SG-level downstream Histogram results."""

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
    "DsHistogramCaptureSettingsModel",
    "DsHistogramCmtsCableModemFilterModel",
    "DsHistogramCmtsPnmParametersModel",
    "DsHistogramCmtsRequestEnvelopeModel",
    "DsHistogramServiceGroupCancelResponse",
    "DsHistogramServiceGroupExecutionModel",
    "DsHistogramServiceGroupOperationRequest",
    "DsHistogramServiceGroupResultsResponse",
    "DsHistogramServiceGroupStartCaptureRequest",
    "DsHistogramServiceGroupStartCaptureResponse",
    "DsHistogramServiceGroupStatusResponse",
]

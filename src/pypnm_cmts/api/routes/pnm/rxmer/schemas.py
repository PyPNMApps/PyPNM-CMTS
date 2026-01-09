# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import (
    ChannelId,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    OperationId,
    TransactionId,
)

from pypnm_cmts.api.common.cmts_request import CmtsRequestEnvelopeModel
from pypnm_cmts.api.common.service.pnm import (
    PnmCaptureExecutionSettings,
    PnmCaptureResultModel,
)
from pypnm_cmts.lib.constants import PnmCaptureFailureReason, PnmCaptureStatus
from pypnm_cmts.lib.types import ServiceGroupId


class RxMerServiceGroupCaptureRequest(BaseModel):
    """Request payload for orchestrated RxMER capture across a serving group."""

    model_config = ConfigDict(extra="ignore")

    cmts: CmtsRequestEnvelopeModel = Field(default_factory=CmtsRequestEnvelopeModel, description="CMTS request envelope.")
    execution: PnmCaptureExecutionSettings = Field(
        default_factory=PnmCaptureExecutionSettings,
        description="Concurrency and retry settings.",
    )

    @model_validator(mode="after")
    def _validate_single_sg(self) -> RxMerServiceGroupCaptureRequest:
        selected = list(self.cmts.serving_group.id)
        if len(selected) != 1:
            raise ValueError("serving_group.id must contain exactly one service group id.")
        if int(selected[0]) <= 0:
            raise ValueError("serving_group.id must be greater than zero.")
        return self


class RxMerServiceGroupCaptureModemResult(BaseModel):
    """Per-modem result details for a serving group RxMER capture."""

    mac_address: MacAddressStr              = Field(..., description="Cable modem MAC address.")
    ipv4: IPv4Str | None                    = Field(default=None, description="Cable modem IPv4 address.")
    ipv6: IPv6Str | None                    = Field(default=None, description="Cable modem IPv6 address.")
    status: PnmCaptureStatus                = Field(default=PnmCaptureStatus.FAILED, description="Capture outcome.")
    message: str                            = Field(default="", description="Capture status message.")
    transaction_id: TransactionId | None    = Field(default=None, description="PyPNM transaction id.")
    operation_id: OperationId | None        = Field(default=None, description="PyPNM operation id.")
    attempts: int                           = Field(default=0, ge=0, description="Number of attempts executed.")
    http_status: int                        = Field(default=0, ge=0, description="HTTP status code from PyPNM.")
    pypnm_status: ServiceStatusCode | None  = Field(default=None, description="PyPNM service status code.")
    started_epoch: float                    = Field(default=0.0, ge=0.0, description="Epoch timestamp when capture started.")
    finished_epoch: float                   = Field(default=0.0, ge=0.0, description="Epoch timestamp when capture finished.")

    @classmethod
    def from_executor_result(cls, result: PnmCaptureResultModel) -> RxMerServiceGroupCaptureModemResult:
        """Convert a generic capture result into an RxMER response model."""
        return cls(
            mac_address     =   result.mac_address,
            ipv4            =   result.ipv4,
            ipv6            =   result.ipv6,
            status          =   result.status,
            message         =   result.message,
            transaction_id  =   result.transaction_id,
            operation_id    =   result.operation_id,
            attempts        =   result.attempts,
            http_status     =   result.http_status,
            pypnm_status    =   result.pypnm_status,
            started_epoch   =   result.started_epoch,
            finished_epoch  =   result.finished_epoch,
        )


class RxMerServiceGroupCaptureResponse(BaseModel):
    """Response payload for orchestrated RxMER capture across a serving group."""

    class SummaryModel(BaseModel):
        """Deterministic response summary for RxMER orchestration."""

        requested_count: int = Field(default=0, ge=0, description="Total modems requested in scope.")
        attempted_count: int = Field(default=0, ge=0, description="Total modems where capture was attempted.")
        success_count: int = Field(default=0, ge=0, description="Total modems with successful capture.")
        failure_count: int = Field(default=0, ge=0, description="Total modems with failed capture.")
        failures_by_reason: dict[PnmCaptureFailureReason, int] = Field(
            default_factory=dict,
            description="Failure counts keyed by failure reason.",
        )
        elapsed_seconds: float = Field(default=0.0, ge=0.0, description="Total elapsed seconds for the orchestration.")

    status: ServiceStatusCode   = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str                = Field(default="", description="Informational or error message.")
    timestamp: str              = Field(default="", description="ISO-8601 timestamp for the response.")
    run_id: str                 = Field(default="", description="Orchestration run identifier.")
    already_running: bool       = Field(default=False, description="Whether an identical capture run is already in-flight.")
    requested_sg_id: ServiceGroupId | None = Field(default=None, description="Requested service group id.")
    requested_channel_ids: list[ChannelId] = Field(
        default_factory=list,
        description="Requested channel id filter list (empty means all).",
    )
    summary: SummaryModel       = Field(default_factory=SummaryModel, description="Deterministic summary for the capture run.")
    total_modems: int       = Field(default=0, ge=0, description="Total modems considered in the serving group.")
    eligible_modems: int    = Field(default=0, ge=0, description="Modems eligible for capture.")
    started_modems: int     = Field(default=0, ge=0, description="Modems where capture was attempted.")
    success_modems: int     = Field(default=0, ge=0, description="Modems with successful capture.")
    failed_modems: int      = Field(default=0, ge=0, description="Modems with failed capture.")
    skipped_modems: int     = Field(default=0, ge=0, description="Modems skipped due to eligibility constraints.")
    results: list[RxMerServiceGroupCaptureModemResult] = Field(
        default_factory=list,
        description="Per-modem capture results.",
    )

    @staticmethod
    def now_timestamp() -> str:
        """Return an ISO-8601 timestamp string."""
        return datetime.now(timezone.utc).isoformat()

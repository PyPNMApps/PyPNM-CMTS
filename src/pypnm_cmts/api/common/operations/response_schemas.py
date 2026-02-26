# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.common.operations.models import (
    OperationResultsSummaryModel,
    OperationStateModel,
    PerModemLinkageRecordModel,
)

PnmResultsPayloadModelT = TypeVar("PnmResultsPayloadModelT", bound=BaseModel)


class PnmCaptureResultsResponseModel(BaseModel, Generic[PnmResultsPayloadModelT]):
    """Generic response envelope for PNM operation `results` endpoints."""

    _results_factory: ClassVar[type[BaseModel] | None] = None

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    results: PnmResultsPayloadModelT | None = Field(default=None, description="Structured results payload.")
    summary: OperationResultsSummaryModel = Field(
        default_factory=OperationResultsSummaryModel,
        description="Linkage results summary (temporary compatibility field).",
    )
    records: list[PerModemLinkageRecordModel] = Field(
        default_factory=list,
        description="Linkage records included in the response (temporary compatibility field).",
    )

    @model_validator(mode="before")
    @classmethod
    def _apply_default_results_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "results" in data:
            return data
        if cls._results_factory is None:
            return data
        payload = dict(data)
        payload["results"] = cls._results_factory()
        return payload


class PnmCaptureOperationResponseModel(BaseModel):
    """Generic response envelope for operation state endpoints with optional state payload."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel | None = Field(default=None, description="Operation state snapshot.")


class PnmCaptureStartResponseModel(BaseModel):
    """Generic response envelope for `startCapture` endpoints."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Service status code.")
    message: str = Field(default="", description="Informational or error message.")
    operation: OperationStateModel = Field(..., description="Initial operation state.")


__all__ = [
    "PnmCaptureOperationResponseModel",
    "PnmCaptureStartResponseModel",
    "PnmCaptureResultsResponseModel",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

import httpx
from pydantic import BaseModel, Field
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import IPv4Str, IPv6Str, MacAddressStr, OperationId, TransactionId

from pypnm_cmts.lib.constants import PnmCaptureFailureReason, PnmCaptureStatus

DEFAULT_HTTP_TIMEOUT_SECONDS = 30.0
DEFAULT_PER_MODEM_TIMEOUT_SECONDS = 30.0
DEFAULT_OVERALL_TIMEOUT_SECONDS = 120.0
DEFAULT_RETRY_DELAY_SECONDS = 5.0
DEFAULT_MAX_WORKERS = 16
ERROR_PER_MODEM_TIMEOUT = "per-modem timeout"


class PnmHttpResponseModel(BaseModel):
    """Normalized HTTP response for PyPNM capture calls."""

    status_code: int = Field(default=0, description="HTTP status code from the PyPNM response.")
    payload: dict[str, object] = Field(default_factory=dict, description="Decoded JSON payload from PyPNM.")
    error_message: str = Field(default="", description="Error message captured during HTTP call, if any.")


class PnmHttpClient:
    """HTTP client interface for PyPNM capture calls."""

    async def post_json(self, path: str, payload: dict[str, object]) -> PnmHttpResponseModel:
        """Post JSON payload to PyPNM and return a normalized response."""
        raise NotImplementedError


class HttpxPnmClient(PnmHttpClient):
    """HTTPX-based PyPNM client with scoped lifecycle management."""

    def __init__(self, base_url: str, timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS) -> None:
        self._base_url = base_url
        self._timeout = float(timeout_seconds)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HttpxPnmClient:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def post_json(self, path: str, payload: dict[str, object]) -> PnmHttpResponseModel:
        if self._client is None:
            return PnmHttpResponseModel(
                status_code=0,
                payload={},
                error_message="http client not initialized",
            )
        try:
            response = await self._client.post(path, json=payload)
        except httpx.RequestError as exc:
            return PnmHttpResponseModel(
                status_code=0,
                payload={},
                error_message=str(exc),
            )
        try:
            payload_data = response.json()
        except ValueError:
            payload_data = {}
        return PnmHttpResponseModel(
            status_code=int(response.status_code),
            payload=payload_data if isinstance(payload_data, dict) else {},
            error_message="",
        )


class PnmCaptureExecutionSettings(BaseModel):
    """Concurrency and retry settings for PNM capture orchestration."""

    max_workers: int = Field(default=DEFAULT_MAX_WORKERS, ge=1, le=256, description="Maximum concurrent capture requests.")
    retry_count: int = Field(default=3, ge=0, le=10, description="Retry attempts for retryable failures.")
    retry_delay_seconds: float = Field(default=DEFAULT_RETRY_DELAY_SECONDS, ge=0.0, le=60.0, description="Delay between retry attempts.")
    per_modem_timeout_seconds: float = Field(
        default=DEFAULT_PER_MODEM_TIMEOUT_SECONDS,
        ge=0.0,
        le=300.0,
        description="Timeout for each per-modem capture attempt; zero disables.",
    )
    overall_timeout_seconds: float = Field(
        default=DEFAULT_OVERALL_TIMEOUT_SECONDS,
        ge=0.0,
        le=600.0,
        description="Overall orchestration timeout; zero disables.",
    )


class PnmCaptureJobModel(BaseModel):
    """Capture job definition for a single cable modem."""

    mac_address: MacAddressStr = Field(..., description="Cable modem MAC address.")
    ipv4: IPv4Str | None = Field(default=None, description="Cable modem IPv4 address, if known.")
    ipv6: IPv6Str | None = Field(default=None, description="Cable modem IPv6 address, if known.")
    path: str = Field(..., description="PyPNM API path for the capture request.")
    payload: dict[str, object] = Field(default_factory=dict, description="Payload for the PyPNM capture request.")


class PnmCaptureParsedModel(BaseModel):
    """Parsed PyPNM capture response payload."""

    status_code: ServiceStatusCode | None = Field(default=None, description="PyPNM service status code, if present.")
    message: str = Field(default="", description="PyPNM response message.")
    transaction_id: TransactionId | None = Field(default=None, description="Transaction id extracted from PyPNM payload.")
    operation_id: OperationId | None = Field(default=None, description="Operation id extracted from PyPNM payload.")
    raw_payload: dict[str, object] = Field(default_factory=dict, description="Raw PyPNM payload for debugging.")


class PnmCaptureResultModel(BaseModel):
    """Result entry for a single capture attempt."""

    mac_address: MacAddressStr = Field(..., description="Cable modem MAC address.")
    ipv4: IPv4Str | None = Field(default=None, description="Cable modem IPv4 address.")
    ipv6: IPv6Str | None = Field(default=None, description="Cable modem IPv6 address.")
    status: PnmCaptureStatus = Field(default=PnmCaptureStatus.FAILED, description="Capture status outcome.")
    message: str = Field(default="", description="Capture status message.")
    transaction_id: TransactionId | None = Field(default=None, description="Transaction identifier from PyPNM.")
    operation_id: OperationId | None = Field(default=None, description="Operation identifier from PyPNM.")
    attempts: int = Field(default=0, ge=0, description="Number of attempts executed.")
    http_status: int = Field(default=0, ge=0, description="HTTP status code returned by PyPNM.")
    pypnm_status: ServiceStatusCode | None = Field(default=None, description="PyPNM service status code.")
    failure_reason: PnmCaptureFailureReason | None = Field(
        default=None,
        description="Failure reason for unsuccessful captures.",
    )
    started_epoch: float = Field(default=0.0, ge=0.0, description="Epoch timestamp for the first attempt.")
    finished_epoch: float = Field(default=0.0, ge=0.0, description="Epoch timestamp for the final attempt.")


class PnmCaptureExecutor:
    """Concurrent capture executor for per-modem PyPNM capture operations."""

    def __init__(
        self,
        http_client: PnmHttpClient,
        settings: PnmCaptureExecutionSettings,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._http_client = http_client
        self._settings = settings
        self._clock = clock or time.time
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    async def run(
        self,
        jobs: list[PnmCaptureJobModel],
        parser: Callable[[PnmHttpResponseModel], PnmCaptureParsedModel],
        should_retry: Callable[[PnmCaptureParsedModel, PnmHttpResponseModel], bool],
    ) -> list[PnmCaptureResultModel]:
        """
        Execute capture jobs concurrently with retry handling.

        Args:
            jobs: The capture jobs to execute.
            parser: Callable that converts a PyPNM HTTP response into a parsed result.
            should_retry: Callable that decides whether a parsed response should be retried.

        Returns:
            A list of capture results in the same order as the input jobs.
        """
        if not jobs:
            return []
        semaphore = asyncio.Semaphore(self._settings.max_workers)
        start_epoch = self._clock()
        task_map: dict[asyncio.Task[PnmCaptureResultModel], int] = {}
        for idx, job in enumerate(jobs):
            task = asyncio.create_task(self._run_job(job, parser, should_retry, semaphore))
            task_map[task] = idx
        if self._settings.overall_timeout_seconds <= 0:
            results = await asyncio.gather(*task_map.keys())
            return list(results)
        done, pending = await asyncio.wait(
            task_map.keys(),
            timeout=self._settings.overall_timeout_seconds,
        )
        results_by_index: dict[int, PnmCaptureResultModel] = {}
        if done:
            completed = await asyncio.gather(*done)
            for task, result in zip(done, completed, strict=False):
                results_by_index[task_map[task]] = result
        if pending:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in pending:
                job_index = task_map[task]
                results_by_index[job_index] = self._build_timeout_result(
                    jobs[job_index],
                    start_epoch,
                    PnmCaptureFailureReason.OVERALL_TIMEOUT,
                    "overall timeout",
                )
        ordered = [results_by_index[idx] for idx in range(len(jobs)) if idx in results_by_index]
        return ordered

    async def _run_job(
        self,
        job: PnmCaptureJobModel,
        parser: Callable[[PnmHttpResponseModel], PnmCaptureParsedModel],
        should_retry: Callable[[PnmCaptureParsedModel, PnmHttpResponseModel], bool],
        semaphore: asyncio.Semaphore,
    ) -> PnmCaptureResultModel:
        started_epoch = self._clock()
        attempt = 0
        parsed: PnmCaptureParsedModel | None = None
        response: PnmHttpResponseModel | None = None
        failure_reason: PnmCaptureFailureReason | None = None

        while True:
            attempt += 1
            async with semaphore:
                response = await self._post_with_timeout(job)
            parsed = parser(response)
            failure_reason = self._resolve_failure_reason(parsed, response)
            if attempt > self._settings.retry_count or not should_retry(parsed, response):
                break
            if self._settings.retry_delay_seconds > 0:
                await asyncio.sleep(self._settings.retry_delay_seconds)

        finished_epoch = self._clock()
        status = self._resolve_status(parsed, response, attempt)
        message = parsed.message if parsed is not None else "unknown response"
        if status == PnmCaptureStatus.SUCCESS:
            failure_reason = None
        return PnmCaptureResultModel(
            mac_address=job.mac_address,
            ipv4=job.ipv4,
            ipv6=job.ipv6,
            status=status,
            message=message,
            transaction_id=parsed.transaction_id if parsed is not None else None,
            operation_id=parsed.operation_id if parsed is not None else None,
            attempts=attempt,
            http_status=response.status_code if response is not None else 0,
            pypnm_status=parsed.status_code if parsed is not None else None,
            failure_reason=failure_reason,
            started_epoch=started_epoch,
            finished_epoch=finished_epoch,
        )

    async def _post_with_timeout(self, job: PnmCaptureJobModel) -> PnmHttpResponseModel:
        timeout_seconds = float(self._settings.per_modem_timeout_seconds)
        if timeout_seconds <= 0:
            return await self._http_client.post_json(job.path, job.payload)
        try:
            return await asyncio.wait_for(
                self._http_client.post_json(job.path, job.payload),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            return PnmHttpResponseModel(
                status_code=0,
                payload={},
                error_message=ERROR_PER_MODEM_TIMEOUT,
            )

    def _build_timeout_result(
        self,
        job: PnmCaptureJobModel,
        started_epoch: float,
        reason: PnmCaptureFailureReason,
        message: str,
    ) -> PnmCaptureResultModel:
        finished_epoch = self._clock()
        return PnmCaptureResultModel(
            mac_address=job.mac_address,
            ipv4=job.ipv4,
            ipv6=job.ipv6,
            status=PnmCaptureStatus.FAILED,
            message=message,
            transaction_id=None,
            operation_id=None,
            attempts=0,
            http_status=0,
            pypnm_status=None,
            failure_reason=reason,
            started_epoch=started_epoch,
            finished_epoch=finished_epoch,
        )

    @staticmethod
    def _resolve_failure_reason(
        parsed: PnmCaptureParsedModel | None,
        response: PnmHttpResponseModel | None,
    ) -> PnmCaptureFailureReason | None:
        if response is None:
            return PnmCaptureFailureReason.UNKNOWN
        if response.error_message != "":
            if response.error_message == ERROR_PER_MODEM_TIMEOUT:
                return PnmCaptureFailureReason.PER_MODEM_TIMEOUT
            return PnmCaptureFailureReason.REQUEST_ERROR
        if response.status_code < 200 or response.status_code >= 300:
            return PnmCaptureFailureReason.HTTP_ERROR
        if parsed is None:
            return PnmCaptureFailureReason.UNKNOWN
        if parsed.status_code != ServiceStatusCode.SUCCESS:
            return PnmCaptureFailureReason.PYPNM_ERROR
        return None

    @staticmethod
    def _resolve_status(
        parsed: PnmCaptureParsedModel | None,
        response: PnmHttpResponseModel | None,
        attempt: int,
    ) -> PnmCaptureStatus:
        if response is None:
            return PnmCaptureStatus.FAILED
        if response.status_code < 200 or response.status_code >= 300:
            return PnmCaptureStatus.FAILED
        if parsed is None:
            return PnmCaptureStatus.FAILED
        if parsed.status_code == ServiceStatusCode.SUCCESS:
            return PnmCaptureStatus.SUCCESS
        if attempt > 0:
            return PnmCaptureStatus.FAILED
        return PnmCaptureStatus.FAILED

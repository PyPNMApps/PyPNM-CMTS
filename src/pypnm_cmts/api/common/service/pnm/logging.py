# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.api.common.operations.logging import short_op_id
from pypnm_cmts.lib.types import PnmCaptureOperationId


def build_start_capture_queued_log(
    operation_name: str,
    operation_id: PnmCaptureOperationId | str,
    scope_sg_count: int,
    scope_mac_count: int,
) -> str:
    return (
        f"{operation_name}-StartCapture [QUEUED] "
        f"operation_id={short_op_id(operation_id)}, "
        f"scope_sg={int(scope_sg_count)}, scope_macs={int(scope_mac_count)}"
    )


def build_request_scope_log(
    operation_name: str,
    requested_sg_count: int,
    requested_mac_count: int,
    resolved_sg_count: int,
    resolved_mac_count: int,
    channel_count: int | None = None,
) -> str:
    base = (
        f"{operation_name}-StartCapture [REQUEST_SCOPE] "
        f"requested_sg_count={int(requested_sg_count)} "
        f"requested_mac_count={int(requested_mac_count)} "
        f"resolved_sg_count={int(resolved_sg_count)} "
        f"resolved_mac_count={int(resolved_mac_count)}"
    )
    if channel_count is None:
        return base
    return f"{base} channel_count={int(channel_count)}"


__all__ = [
    "build_request_scope_log",
    "build_start_capture_queued_log",
]

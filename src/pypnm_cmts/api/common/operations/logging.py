# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.lib.types import PnmCaptureOperationId

OPERATION_ID_LOG_LENGTH = 6


def short_op_id(operation_id: PnmCaptureOperationId | str) -> str:
    value = str(operation_id)
    if value == "":
        return value
    return value[:OPERATION_ID_LOG_LENGTH]


__all__ = [
    "short_op_id",
]

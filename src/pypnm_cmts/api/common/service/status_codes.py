# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

"""
Shared status code contract for PyPNM-CMTS.

PyPNM reserved range: <= 9999
PyPNM-CMTS reserved range: >= 10000
Do not renumber or reuse PyPNM codes.
"""
from __future__ import annotations

from enum import IntEnum

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

CMTS_STATUS_CODE_BASE = 10000


class CmtsStatusCode(IntEnum):
    """
    PyPNM reserved range: <= 9999
    PyPNM-CMTS reserved range: >= 10000
    Do not renumber or reuse PyPNM codes.
    """

    CMTS_UNKNOWN = CMTS_STATUS_CODE_BASE
    CMTS_NOT_READY = CMTS_STATUS_CODE_BASE + 1
    CMTS_TOPOLOGY_UNAVAILABLE = CMTS_STATUS_CODE_BASE + 2


__all__ = [
    "CMTS_STATUS_CODE_BASE",
    "CmtsStatusCode",
    "ServiceStatusCode",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.common.service.status_codes import (
    CMTS_STATUS_CODE_BASE,
    CmtsStatusCode,
)


def test_cmts_status_codes_start_at_reserved_base() -> None:
    values = [int(code) for code in CmtsStatusCode]
    assert min(values) >= CMTS_STATUS_CODE_BASE


def test_cmts_status_codes_do_not_overlap_pypnm_range() -> None:
    values = [int(code) for code in CmtsStatusCode]
    assert min(values) >= CMTS_STATUS_CODE_BASE


def test_pypnm_status_codes_stay_below_reserved_boundary() -> None:
    values = [int(code) for code in ServiceStatusCode]
    assert max(values) <= CMTS_STATUS_CODE_BASE - 1

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.docsis.cm_snmp_operation import FecSummaryType

from pypnm_cmts.api.common.cmts_request import (
    CmtsRequestEnvelopeModel,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.schemas import (
    FecSummaryServiceGroupStartCaptureRequest,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.service import (
    FecSummaryServiceGroupOperationService,
)


def test_fec_summary_start_capture_request_accepts_capture_settings() -> None:
    request = FecSummaryServiceGroupStartCaptureRequest.model_validate(
        {
            "cmts": {},
            "capture_settings": {
                "fec_summary_type": 2,
            },
        }
    )
    assert request.capture_settings.fec_summary_type == FecSummaryType.TEN_MIN


def test_fec_summary_build_request_context_persists_fec_summary_type() -> None:
    request = FecSummaryServiceGroupStartCaptureRequest(
        cmts=CmtsRequestEnvelopeModel(),
        capture_settings={"fec_summary_type": FecSummaryType.TWENTY_FOUR_HOUR},
    )
    context = FecSummaryServiceGroupOperationService._build_request_context(request)
    assert context.fec_summary_type == int(FecSummaryType.TWENTY_FOUR_HOUR.value)

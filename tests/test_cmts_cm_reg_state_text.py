# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.docsis.data_type.cmts_cm_reg_state import (
    CmtsCmRegStateText,
    decode_cmts_cm_reg_state,
)


def test_decode_maps_known_values() -> None:
    assert decode_cmts_cm_reg_state(8) == CmtsCmRegStateText.operational
    assert decode_cmts_cm_reg_state(2) == CmtsCmRegStateText.initialRanging


def test_decode_maps_unknown_to_other() -> None:
    assert decode_cmts_cm_reg_state(999) == CmtsCmRegStateText.other

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm_cmts.docsis.data_type.cmts_cm_reg_state import CmtsCmRegStateText
from pypnm_cmts.lib.types import CmtsCmRegState


class CmtsCmRegStateModel(BaseModel):
    """DOCSIS CM registration status value and token."""

    status: CmtsCmRegState = Field(..., description="DOCSIS CmtsCmRegState numeric value.")
    text: CmtsCmRegStateText = Field(..., description="DOCSIS CmtsCmRegState decoded token.")


__all__ = [
    "CmtsCmRegStateModel",
]

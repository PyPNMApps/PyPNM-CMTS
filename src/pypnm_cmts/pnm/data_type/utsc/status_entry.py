# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel
from pypnm.docsis.data_type.enums import MeasStatusType
from pypnm.lib.types import InterfaceIndex


class DocsPnmCmtsUtscStatusEntry(BaseModel):
    """docsPnmCmtsUtscStatusEntry table fields."""

    docsPnmCmtsUtscStatusMeasStatus: MeasStatusType | None = None
    docsPnmCmtsUtscStatusCalibrationConstantK: int | None = None


class DocsPnmCmtsUtscStatusRecord(BaseModel):
    """Container for a single docsPnmCmtsUtscStatus row."""

    if_index: InterfaceIndex
    cfg_index: int
    entry: DocsPnmCmtsUtscStatusEntry


__all__ = [
    "DocsPnmCmtsUtscStatusEntry",
    "DocsPnmCmtsUtscStatusRecord",
]

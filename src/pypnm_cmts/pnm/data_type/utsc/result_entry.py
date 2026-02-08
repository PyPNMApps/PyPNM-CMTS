# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel
from pypnm.lib.types import (
    FrequencyHz,
    InterfaceIndex,
    ResolutionBw,
    SampleIndex,
    TimeStamp,
)


class DocsPnmCmtsUtscResultEntry(BaseModel):
    """docsPnmCmtsUtscResultEntry table fields."""

    docsPnmCmtsUtscResultSampleRate: FrequencyHz | None = None
    docsPnmCmtsUtscResultUsSampleSize: SampleIndex | None = None
    docsPnmCmtsUtscResultSampleTimestamp: TimeStamp | None = None
    docsPnmCmtsUtscResultResolutionBw: ResolutionBw | None = None
    docsPnmCmtsUtscResultOutput: bytes | None = None
    docsPnmCmtsUtscResultCalibrationConstantK: int | None = None


class DocsPnmCmtsUtscResultRecord(BaseModel):
    """Container for a single docsPnmCmtsUtscResult row."""

    if_index: InterfaceIndex
    cfg_index: int
    entry: DocsPnmCmtsUtscResultEntry


__all__ = [
    "DocsPnmCmtsUtscResultEntry",
    "DocsPnmCmtsUtscResultRecord",
]

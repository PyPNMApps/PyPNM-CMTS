# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel
from pypnm.lib.types import InterfaceIndex

from pypnm_cmts.pnm.data_type.utsc.enums import (
    DocsPnmCmtsUtscCapabOutputFormatBit,
    DocsPnmCmtsUtscCapabTriggerModeBit,
    DocsPnmCmtsUtscCapabWindowBit,
)


class DocsPnmCmtsUtscCapabEntry(BaseModel):
    """docsPnmCmtsUtscCapabEntry table fields."""

    docsPnmCmtsUtscCapabTriggerMode: set[DocsPnmCmtsUtscCapabTriggerModeBit] | None = None
    docsPnmCmtsUtscCapabOutputFormat: set[DocsPnmCmtsUtscCapabOutputFormatBit] | None = None
    docsPnmCmtsUtscCapabWindow: set[DocsPnmCmtsUtscCapabWindowBit] | None = None
    docsPnmCmtsUtscCapabDescription: str | None = None


class DocsPnmCmtsUtscCapabRecord(BaseModel):
    """Container for a single docsPnmCmtsUtscCapab row."""

    if_index: InterfaceIndex
    entry: DocsPnmCmtsUtscCapabEntry


__all__ = [
    "DocsPnmCmtsUtscCapabEntry",
    "DocsPnmCmtsUtscCapabRecord",
]

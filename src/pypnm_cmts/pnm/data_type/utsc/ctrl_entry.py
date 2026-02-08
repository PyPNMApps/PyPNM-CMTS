# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel
from pypnm.lib.types import InterfaceIndex


class DocsPnmCmtsUtscCtrlEntry(BaseModel):
    """docsPnmCmtsUtscCtrlEntry table fields."""

    docsPnmCmtsUtscCtrlInitiateTest: bool | None = None


class DocsPnmCmtsUtscCtrlRecord(BaseModel):
    """Container for a single docsPnmCmtsUtscCtrl row."""

    if_index: InterfaceIndex
    cfg_index: int
    entry: DocsPnmCmtsUtscCtrlEntry


__all__ = [
    "DocsPnmCmtsUtscCtrlEntry",
    "DocsPnmCmtsUtscCtrlRecord",
]

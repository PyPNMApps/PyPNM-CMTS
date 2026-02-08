# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel
from pypnm.lib.types import FileNameStr, InterfaceIndex, MacAddressStr

from pypnm_cmts.lib.types import InterfaceIndexOrZero, PnmDestinationIndex, PnmRowStatus
from pypnm_cmts.pnm.data_type.utsc.enums import (
    DocsPnmCmtsUtscCfgBurstIuc,
    DocsPnmCmtsUtscCfgOutputFormat,
    DocsPnmCmtsUtscCfgTriggerMode,
    DocsPnmCmtsUtscCfgWindow,
)


class DocsPnmCmtsUtscCfgEntry(BaseModel):
    """docsPnmCmtsUtscCfgEntry table fields."""

    docsPnmCmtsUtscCfgIndex: int | None = None
    docsPnmCmtsUtscCfgLogicalChIfIndex: InterfaceIndexOrZero | None = None
    docsPnmCmtsUtscCfgTriggerMode: DocsPnmCmtsUtscCfgTriggerMode | None = None
    docsPnmCmtsUtscCfgMinislotCount: int | None = None
    docsPnmCmtsUtscCfgSid: int | None = None
    docsPnmCmtsUtscCfgCmMacAddr: MacAddressStr | None = None
    docsPnmCmtsUtscCfgTimestamp: int | None = None
    docsPnmCmtsUtscCfgCenterFreq: int | None = None
    docsPnmCmtsUtscCfgSpan: int | None = None
    docsPnmCmtsUtscCfgNumBins: int | None = None
    docsPnmCmtsUtscCfgAveraging: int | None = None
    docsPnmCmtsUtscCfgFilename: FileNameStr | None = None
    docsPnmCmtsUtscCfgQualifyCenterFreq: int | None = None
    docsPnmCmtsUtscCfgQualifyBw: int | None = None
    docsPnmCmtsUtscCfgQualifyThrshld: int | None = None
    docsPnmCmtsUtscCfgWindow: DocsPnmCmtsUtscCfgWindow | None = None
    docsPnmCmtsUtscCfgOutputFormat: DocsPnmCmtsUtscCfgOutputFormat | None = None
    docsPnmCmtsUtscCfgRepeatPeriod: int | None = None
    docsPnmCmtsUtscCfgFreeRunDuration: int | None = None
    docsPnmCmtsUtscCfgTriggerCount: int | None = None
    docsPnmCmtsUtscCfgStatus: PnmRowStatus | None = None
    docsPnmCmtsUtscCfgBurstIuc: DocsPnmCmtsUtscCfgBurstIuc | None = None
    docsPnmCmtsUtscCfgMaxResultsPerFile: int | None = None
    docsPnmCmtsUtscCfgDestinationIndex: PnmDestinationIndex | None = None


class DocsPnmCmtsUtscCfgRecord(BaseModel):
    """Container for a single docsPnmCmtsUtscCfg row."""

    if_index: InterfaceIndex
    cfg_index: int
    entry: DocsPnmCmtsUtscCfgEntry


__all__ = [
    "DocsPnmCmtsUtscCfgEntry",
    "DocsPnmCmtsUtscCfgRecord",
]

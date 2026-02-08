# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.docsis.data_type.enums import MeasStatusType
from pypnm.lib.types import InterfaceIndex

from pypnm_cmts.pnm.data_type.utsc import (
    DocsPnmCmtsUtscCapabEntry,
    DocsPnmCmtsUtscCapabOutputFormatBit,
    DocsPnmCmtsUtscCapabRecord,
    DocsPnmCmtsUtscCapabTriggerModeBit,
    DocsPnmCmtsUtscCapabWindowBit,
    DocsPnmCmtsUtscCfgEntry,
    DocsPnmCmtsUtscCfgOutputFormat,
    DocsPnmCmtsUtscCfgRecord,
    DocsPnmCmtsUtscCfgTriggerMode,
    DocsPnmCmtsUtscCfgWindow,
    DocsPnmCmtsUtscCtrlEntry,
    DocsPnmCmtsUtscResultEntry,
    DocsPnmCmtsUtscStatusEntry,
)


def test_utsc_capab_entry_model() -> None:
    entry = DocsPnmCmtsUtscCapabEntry(
        docsPnmCmtsUtscCapabTriggerMode={DocsPnmCmtsUtscCapabTriggerModeBit.FREE_RUNNING},
        docsPnmCmtsUtscCapabOutputFormat={DocsPnmCmtsUtscCapabOutputFormatBit.FFT_POWER},
        docsPnmCmtsUtscCapabWindow={DocsPnmCmtsUtscCapabWindowBit.HANN},
        docsPnmCmtsUtscCapabDescription="sample",
    )
    record = DocsPnmCmtsUtscCapabRecord(if_index=InterfaceIndex(10), entry=entry)
    assert int(record.if_index) == 10
    assert record.entry.docsPnmCmtsUtscCapabDescription == "sample"


def test_utsc_cfg_entry_model() -> None:
    entry = DocsPnmCmtsUtscCfgEntry(
        docsPnmCmtsUtscCfgTriggerMode=DocsPnmCmtsUtscCfgTriggerMode.FREE_RUNNING,
        docsPnmCmtsUtscCfgWindow=DocsPnmCmtsUtscCfgWindow.RECTANGULAR,
        docsPnmCmtsUtscCfgOutputFormat=DocsPnmCmtsUtscCfgOutputFormat.FFT_POWER,
        docsPnmCmtsUtscCfgCenterFreq=25000000,
    )
    record = DocsPnmCmtsUtscCfgRecord(
        if_index=InterfaceIndex(20),
        cfg_index=1,
        entry=entry,
    )
    assert int(record.if_index) == 20
    assert record.cfg_index == 1


def test_utsc_ctrl_status_result_entry_models() -> None:
    ctrl = DocsPnmCmtsUtscCtrlEntry(docsPnmCmtsUtscCtrlInitiateTest=True)
    status = DocsPnmCmtsUtscStatusEntry(
        docsPnmCmtsUtscStatusMeasStatus=MeasStatusType.BUSY,
        docsPnmCmtsUtscStatusCalibrationConstantK=12,
    )
    result = DocsPnmCmtsUtscResultEntry(
        docsPnmCmtsUtscResultSampleRate=10240000,
        docsPnmCmtsUtscResultOutput=b"\x01\x02",
    )
    assert ctrl.docsPnmCmtsUtscCtrlInitiateTest is True
    assert status.docsPnmCmtsUtscStatusMeasStatus == MeasStatusType.BUSY
    assert result.docsPnmCmtsUtscResultOutput == b"\x01\x02"

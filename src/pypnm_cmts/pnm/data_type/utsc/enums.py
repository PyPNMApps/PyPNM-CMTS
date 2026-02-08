# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from enum import IntEnum


class DocsPnmCmtsUtscCapabTriggerModeBit(IntEnum):
    OTHER = 0
    FREE_RUNNING = 1
    MINI_SLOT_COUNT = 2
    SID = 3
    IDLE_SID = 4
    CM_MAC = 5
    QUIET_PROBE_SYMBOL = 6
    BURST_IUC = 7
    TIMESTAMP = 8
    ACTIVE_PROBE_SYMBOL = 9


class DocsPnmCmtsUtscCapabOutputFormatBit(IntEnum):
    OTHER = 0
    TIME_IQ = 1
    FFT_POWER = 2
    RAW_ADC = 3
    FFT_IQ = 4
    FFT_AMPLITUDE = 5
    FFT_DB = 6


class DocsPnmCmtsUtscCapabWindowBit(IntEnum):
    OTHER = 0
    RECTANGULAR = 1
    HANN = 2
    BLACKMAN_HARRIS = 3
    HAMMING = 4
    FLAT_TOP = 5
    GAUSSIAN = 6
    CHEBYSHEV = 7


class DocsPnmCmtsUtscCfgTriggerMode(IntEnum):
    OTHER = 1
    FREE_RUNNING = 2
    MINI_SLOT_COUNT = 3
    SID = 4
    IDLE_SID = 5
    CM_MAC = 6
    QUIET_PROBE_SYMBOL = 7
    BURST_IUC = 8
    TIMESTAMP = 9
    ACTIVE_PROBE_SYMBOL = 10


class DocsPnmCmtsUtscCfgWindow(IntEnum):
    OTHER = 1
    RECTANGULAR = 2
    HANN = 3
    BLACKMAN_HARRIS = 4
    HAMMING = 5
    FLAT_TOP = 6
    GAUSSIAN = 7
    CHEBYSHEV = 8


class DocsPnmCmtsUtscCfgOutputFormat(IntEnum):
    TIME_IQ = 1
    FFT_POWER = 2
    RAW_ADC = 3
    FFT_IQ = 4
    FFT_AMPLITUDE = 5
    FFT_DB = 6


class DocsPnmCmtsUtscCfgBurstIuc(IntEnum):
    OTHER = 1
    IUC1 = 2
    IUC2 = 3
    IUC3 = 4
    IUC4 = 5
    IUC5 = 6
    IUC6 = 7
    IUC9 = 8
    IUC10 = 9
    IUC11 = 10
    IUC12 = 11
    IUC13 = 12


__all__ = [
    "DocsPnmCmtsUtscCapabOutputFormatBit",
    "DocsPnmCmtsUtscCapabTriggerModeBit",
    "DocsPnmCmtsUtscCapabWindowBit",
    "DocsPnmCmtsUtscCfgBurstIuc",
    "DocsPnmCmtsUtscCfgOutputFormat",
    "DocsPnmCmtsUtscCfgTriggerMode",
    "DocsPnmCmtsUtscCfgWindow",
]

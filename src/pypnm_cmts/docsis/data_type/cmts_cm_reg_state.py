# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from enum import Enum


class CmtsCmRegStateText(str, Enum):
    other = "other"
    initialRanging = "initialRanging"
    rangingAutoAdjComplete = "rangingAutoAdjComplete"
    dhcpv4Complete = "dhcpv4Complete"
    registrationComplete = "registrationComplete"
    operational = "operational"
    bpiInit = "bpiInit"
    startEae = "startEae"
    startDhcpv4 = "startDhcpv4"
    startDhcpv6 = "startDhcpv6"
    dhcpv6Complete = "dhcpv6Complete"
    startConfigFileDownload = "startConfigFileDownload"
    configFileDownloadComplete = "configFileDownloadComplete"
    startRegistration = "startRegistration"
    forwardingDisabled = "forwardingDisabled"
    rfMuteAll = "rfMuteAll"


def decode_cmts_cm_reg_state(value: int) -> CmtsCmRegStateText:
    """
    Decode a DOCSIS CmtsCmRegState numeric value into its MIB token.

    Unknown or unmapped values return CmtsCmRegStateText.other.
    The MIB defines other(1), which is explicitly mapped here.
    Tokens correspond to the DOCSIS MIB enumeration labels and values.
    """
    match int(value):
        case 1:
            return CmtsCmRegStateText.other
        case 2:
            return CmtsCmRegStateText.initialRanging
        case 4:
            return CmtsCmRegStateText.rangingAutoAdjComplete
        case 5:
            return CmtsCmRegStateText.dhcpv4Complete
        case 6:
            return CmtsCmRegStateText.registrationComplete
        case 8:
            return CmtsCmRegStateText.operational
        case 9:
            return CmtsCmRegStateText.bpiInit
        case 10:
            return CmtsCmRegStateText.startEae
        case 11:
            return CmtsCmRegStateText.startDhcpv4
        case 12:
            return CmtsCmRegStateText.startDhcpv6
        case 13:
            return CmtsCmRegStateText.dhcpv6Complete
        case 14:
            return CmtsCmRegStateText.startConfigFileDownload
        case 15:
            return CmtsCmRegStateText.configFileDownloadComplete
        case 16:
            return CmtsCmRegStateText.startRegistration
        case 17:
            return CmtsCmRegStateText.forwardingDisabled
        case 18:
            return CmtsCmRegStateText.rfMuteAll
        case _:
            return CmtsCmRegStateText.other


__all__ = [
    "CmtsCmRegStateText",
    "decode_cmts_cm_reg_state",
]

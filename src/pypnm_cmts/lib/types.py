# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

"""Type aliases for PyPNM-CMTS."""
from __future__ import annotations

from typing import NewType

from pypnm.lib.types import InterfaceIndex, IPv4Str, IPv6Str, MacAddressStr

MacAddressExist = NewType("MacAddressExist", bool)

NodeName        = NewType("NodeName", str)
MdCmSgId        = NewType("MdCmSgId", int)
MdNodeStatus    = tuple[InterfaceIndex, NodeName, MdCmSgId]

CmtsCmRegStatusId       = NewType("CmtsCmRegStatusId", int)
CmtsCmRegStatusMacAddr  = tuple[CmtsCmRegStatusId, MacAddressStr]
CableModemIndex         = NewType("CableModemIndex", int)
IPv6LinkLocalStr        = NewType("IPv6LinkLocalStr", IPv6Str)
RegisterCmMacInetAddress = tuple[
    CableModemIndex,
    MacAddressStr,
    IPv4Str,
    IPv6Str,
    IPv6LinkLocalStr,
]
RegisterCmInetAddress = tuple[
    IPv4Str,
    IPv6Str,
    IPv6LinkLocalStr,
]
CmtsCmRegState          = NewType("CmtsCmRegState", int)
InterfaceIndexOrZero    = NewType("InterfaceIndexOrZero", int)
MdIfIndex               = InterfaceIndexOrZero
RcpId                   = NewType("RcpId", str)
ChSetId                 = NewType("ChSetId", int)
DocsisQosVersion        = NewType("DocsisQosVersion", int)
DateAndTime             = NewType("DateAndTime", str)
EnergyMgtBits           = NewType("EnergyMgtBits", int)
InetAddressIPv4         = IPv4Str
InetAddressIPv6         = IPv6Str

__all__ = [
    "MacAddressExist",
    "NodeName",
    "MdCmSgId",
    "MdNodeStatus",
    "CmtsCmRegStatusId",
    "CmtsCmRegStatusMacAddr",
    "CableModemIndex",
    "IPv6LinkLocalStr",
    "RegisterCmMacInetAddress",
    "RegisterCmInetAddress",
    "CmtsCmRegState",
    "InterfaceIndexOrZero",
    "MdIfIndex",
    "RcpId",
    "ChSetId",
    "DocsisQosVersion",
    "DateAndTime",
    "EnergyMgtBits",
    "InetAddressIPv4",
    "InetAddressIPv6",
]

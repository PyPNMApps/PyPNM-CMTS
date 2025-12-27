# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

"""Type aliases for PyPNM-CMTS."""
from __future__ import annotations

from typing import NewType

from pypnm.lib.types import (
    InterfaceIndex,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    PathLike,
    SnmpIndex,
)

IPv6LinkLocalStr        = NewType("IPv6LinkLocalStr", IPv6Str)
CableModemIndex         = NewType("CableModemIndex", SnmpIndex)
CmRegSgId               = NewType("CmRegSgId", int)
RegisterCmMacInetAddress = tuple[CableModemIndex, MacAddressStr, IPv4Str, IPv6Str, IPv6LinkLocalStr]
RegisterCmInetAddress   = tuple[IPv4Str, IPv6Str, IPv6LinkLocalStr]

MacAddressExist = NewType("MacAddressExist", bool)

CoordinationElectionName = NewType("CoordinationElectionName", str)
LeaderId                 = NewType("LeaderId", str)
OwnerId                  = NewType("OwnerId", str)
ServiceGroupId           = NewType("ServiceGroupId", int)
TickIndex                = NewType("TickIndex", int)
OrchestratorRunId        = NewType("OrchestratorRunId", str)
CoordinationPath         = PathLike

NodeName        = NewType("NodeName", str)
MdCmSgId        = NewType("MdCmSgId", int)
MdDsSgId        = NewType("MdDsSgId", int)
MdUsSgId        = NewType("MdUsSgId", int)
MdNodeStatus    = tuple[InterfaceIndex, NodeName, MdCmSgId]

CmtsCmRegStatusId       = NewType("CmtsCmRegStatusId", int)
CmtsCmRegStatusMacAddr  = tuple[CmtsCmRegStatusId, MacAddressStr]
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
    "IPv6LinkLocalStr",
    "CableModemIndex",
    "CmRegSgId",
    "CoordinationElectionName",
    "LeaderId",
    "OwnerId",
    "ServiceGroupId",
    "TickIndex",
    "OrchestratorRunId",
    "CoordinationPath",
    "NodeName",
    "MdCmSgId",
    "MdDsSgId",
    "MdUsSgId",
    "MdNodeStatus",
    "CmtsCmRegStatusId",
    "CmtsCmRegStatusMacAddr",
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
    "RegisterCmMacInetAddress",
    "RegisterCmInetAddress",
]

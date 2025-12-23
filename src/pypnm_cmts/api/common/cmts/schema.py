# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm.lib.types import HostNameStr, InetAddressStr
from pypnm.snmp.snmp_v2c import Snmp_v2c


class CmtsTarget(BaseModel):
    """
    CMTS connection target details.
    """
    hostname: HostNameStr = Field(..., description="CMTS hostname or label.")
    ip_address: InetAddressStr = Field(..., description="CMTS IP address.")

class CmtsSnmpConfig(BaseModel):
    """
    SNMP configuration settings for CMTS requests.
    """
    community: str = Field(..., description="SNMPv2c community string.")
    port: int = Field(default=Snmp_v2c.SNMP_PORT, description="SNMP port.")


class CommonCmtsRequest(BaseModel):
    """
    Base CMTS request with target and SNMP configuration.
    """
    cmts: CmtsTarget = Field(..., description="CMTS connection details.")
    snmp: CmtsSnmpConfig = Field(..., description="SNMP connection settings.")

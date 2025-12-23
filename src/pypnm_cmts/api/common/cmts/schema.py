# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm.api.routes.common.classes.common_endpoint_classes.schema.base_snmp import SNMPConfig
from pypnm.lib.types import HostNameStr, InetAddressStr
from pypnm.snmp.snmp_v2c import Snmp_v2c

class CmtsSnmpConfig(SNMPConfig):
    """
    SNMP configuration settings for CMTS requests.
    """
    port: int = Field(default=Snmp_v2c.SNMP_PORT, description="SNMP port.")
class CmtsTarget(BaseModel):
    """
    CMTS connection target details.
    """
    hostname: HostNameStr = Field(..., description="CMTS hostname or label.")
    ip_address: InetAddressStr = Field(..., description="CMTS IP address.")

class CommonCmtsRequest(BaseModel):
    """
    Common request model for CMTS endpoints.
    """
    cmts: CmtsTarget = Field(..., description="CMTS connection details.")
    snmp: CmtsSnmpConfig = Field(..., description="SNMP connection settings.")

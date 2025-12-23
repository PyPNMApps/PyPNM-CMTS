# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import HostNameStr, InetAddressStr
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class CmtsSnmpConfig(BaseModel):
    """
    SNMP configuration settings for CMTS requests.
    """
    community: str = Field(..., description="SNMPv2c community string.")
    port: int = Field(default=Snmp_v2c.SNMP_PORT, description="SNMP port.")


class CmtsTarget(BaseModel):
    """
    CMTS connection target details.
    """
    hostname: HostNameStr = Field(default="", description="CMTS hostname or label.")
    ip_address: InetAddressStr = Field(default="", description="CMTS IP address.")


class CmtsSysDescrRequest(BaseModel):
    """
    Request model for CMTS sysDescr retrieval.
    """
    cmts: CmtsTarget = Field(..., description="CMTS connection details.")
    snmp: CmtsSnmpConfig = Field(..., description="SNMP connection settings.")


class CmtsSysDescrResponse(BaseModel):
    """
    Response model for CMTS sysDescr retrieval.
    """
    hostname: HostNameStr = Field(default="", description="CMTS hostname or label.")
    ip_address: InetAddressStr = Field(default="", description="CMTS IP address.")
    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Result status code.")
    message: str = Field(default="", description="Informational or error message.")
    results: CmtsSysDescrModel = Field(default_factory=CmtsSysDescrModel.empty, description="Parsed CMTS sysDescr data.")

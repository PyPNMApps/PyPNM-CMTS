# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pypnm.api.routes.common.classes.common_endpoint_classes.schema.base_snmp import (
    SNMPv2c,
    SNMPv3,
    to_camel,
)
from pypnm.lib.types import HostNameStr
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings


class CmtsSnmpConfig(BaseModel):
    """
    SNMP configuration model supporting both v2c and optional v3 settings.
    """
    model_config        = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    port: int           = Field(default=Snmp_v2c.SNMP_PORT, description="SNMP port.")

    if CmtsSystemConfigSettings.cmts_snmp_v2c_enabled(0):
        snmp_v2c: SNMPv2c   = Field(default_factory=SNMPv2c, description="SNMP v2c settings")

    if CmtsSystemConfigSettings.cmts_snmp_v3_enabled(0):
        snmp_v3: SNMPv3     = Field(default_factory=SNMPv3, description="SNMP v3 settings")


class CmtsTarget(BaseModel):
    """
    CMTS connection target details.
    """
    hostname: HostNameStr = Field(default=CmtsSystemConfigSettings.cmts_device_hostname(0), description="CMTS hostname or label.")

class CommonCmtsRequest(BaseModel):
    """
    Common request model for CMTS endpoints.
    """
    cmts: CmtsTarget = Field(..., description="CMTS connection details.")
    snmp: CmtsSnmpConfig = Field(..., description="SNMP connection settings.")

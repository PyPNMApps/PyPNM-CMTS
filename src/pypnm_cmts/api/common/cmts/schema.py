# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pypnm.api.routes.common.classes.common_endpoint_classes.schema.base_snmp import (
    SNMPv2c,
    SNMPv3,
    to_camel,
)
from pypnm.lib.types import HostNameStr
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.api.common.cmts_request import CmtsRequestEnvelopeModel
from pypnm_cmts.config.orchestrator_config import (
    ENV_ADAPTER_HOSTNAME,
    ENV_ADAPTER_READ_COMMUNITY,
)
from pypnm_cmts.config.request_defaults import CmtsRequestDefaults
from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings


class CmtsSnmpConfig(BaseModel):
    """
    SNMP configuration model supporting both v2c and optional v3 settings.
    """
    model_config        = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    port: int           = Field(default=Snmp_v2c.SNMP_PORT, description="SNMP port.")

    snmp_v2c: SNMPv2c   = Field(default_factory=SNMPv2c, description="SNMP v2c settings")
    snmp_v3: SNMPv3 | None = Field(default=None, description="SNMP v3 settings")


class CmtsTarget(BaseModel):
    """
    CMTS connection target details.
    """
    hostname: HostNameStr = Field(
        default_factory=lambda: CmtsSystemConfigSettings.cmts_device_hostname(0),
        description="CMTS hostname or label.",
    )

class CommonCmtsRequest(BaseModel):
    """
    Common request model for CMTS endpoints.
    """
    cmts: CmtsRequestEnvelopeModel = Field(default_factory=CmtsRequestEnvelopeModel, description="CMTS request envelope.")
    target: CmtsTarget = Field(default_factory=CmtsTarget, description="CMTS connection details.")
    snmp: CmtsSnmpConfig = Field(default_factory=CmtsSnmpConfig, description="SNMP connection settings.")

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_request(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        if "target" in values:
            return values
        cmts_value = values.get("cmts")
        if isinstance(cmts_value, dict) and "hostname" in cmts_value:
            normalized = dict(values)
            normalized["target"] = cmts_value
            normalized["cmts"] = {}
            return normalized
        return values

    @model_validator(mode="after")
    def _apply_request_defaults(self) -> CommonCmtsRequest:
        defaults = CmtsRequestDefaults.from_system_config()
        self.cmts = self.cmts.apply_defaults(defaults)
        if "target" not in self.model_fields_set and self.target.hostname == "":
            hostname_value = os.environ.get(ENV_ADAPTER_HOSTNAME, "").strip()
            if hostname_value == "":
                hostname_value = CmtsSystemConfigSettings.cmts_device_hostname(0)
            self.target.hostname = HostNameStr(hostname_value)
        if "snmp" not in self.model_fields_set:
            community_value = os.environ.get(ENV_ADAPTER_READ_COMMUNITY, "").strip()
            if community_value == "":
                community_value = CmtsSystemConfigSettings.cmts_snmp_v2c_read_community(0)
            self.snmp.snmp_v2c.community = community_value
            self.snmp.port = int(CmtsSystemConfigSettings.cmts_snmp_v2c_port(0))
        return self

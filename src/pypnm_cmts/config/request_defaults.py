# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os

from pydantic import BaseModel, Field
from pypnm.config.system_config_settings import SystemConfigSettings
from pypnm.lib.types import IPv4Str, IPv6Str, SnmpWriteCommunity

ENV_CM_SNMPV2C_WRITE_COMMUNITY = "PYPNM_CMTS_CM_SNMPV2C_WRITE_COMMUNITY"
ENV_CM_TFTP_IPV4 = "PYPNM_CMTS_CM_TFTP_IPV4"
ENV_CM_TFTP_IPV6 = "PYPNM_CMTS_CM_TFTP_IPV6"


class CmtsRequestDefaults(BaseModel):
    """Default override values for CMTS request envelopes."""

    cm_snmpv2c_write_community: SnmpWriteCommunity | None = Field(
        default=None, description="Default SNMPv2c write community for CM overrides."
    )
    cm_tftp_ipv4: IPv4Str | None = Field(default=None, description="Default TFTP IPv4 override for CM requests.")
    cm_tftp_ipv6: IPv6Str | None = Field(default=None, description="Default TFTP IPv6 override for CM requests.")

    @classmethod
    def from_system_config(cls) -> CmtsRequestDefaults:
        """Load defaults from system.json with CLI environment overrides."""
        env_write = os.environ.get(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "").strip()
        if env_write == "":
            config_write = str(SystemConfigSettings.snmp_write_community()).strip()
        else:
            config_write = env_write

        env_ipv4 = os.environ.get(ENV_CM_TFTP_IPV4, "").strip()
        if env_ipv4 == "":
            config_ipv4 = str(SystemConfigSettings.bulk_tftp_ip_v4()).strip()
        else:
            config_ipv4 = env_ipv4

        env_ipv6 = os.environ.get(ENV_CM_TFTP_IPV6, "").strip()
        if env_ipv6 == "":
            config_ipv6 = str(SystemConfigSettings.bulk_tftp_ip_v6()).strip()
        else:
            config_ipv6 = env_ipv6

        return cls(
            cm_snmpv2c_write_community=SnmpWriteCommunity(config_write) if config_write != "" else None,
            cm_tftp_ipv4=IPv4Str(config_ipv4) if config_ipv4 != "" else None,
            cm_tftp_ipv6=IPv6Str(config_ipv6) if config_ipv6 != "" else None,
        )


__all__ = [
    "CmtsRequestDefaults",
    "ENV_CM_SNMPV2C_WRITE_COMMUNITY",
    "ENV_CM_TFTP_IPV4",
    "ENV_CM_TFTP_IPV6",
]

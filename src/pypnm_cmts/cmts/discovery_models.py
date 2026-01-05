# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.types import HostNameStr, IPv4Str, IPv6Str, MacAddressStr

from pypnm_cmts.lib.types import (
    ChSetId,
    CmtsCmRegState,
    IPv6LinkLocalStr,
    ServiceGroupId,
)


class RegisteredCableModemModel(BaseModel):
    mac: MacAddressStr = Field(default=MacAddressStr(""), description="Cable modem MAC address.")
    ipv4: IPv4Str = Field(default=IPv4Str(""), description="Cable modem IPv4 address when available.")
    ipv6: IPv6Str = Field(default=IPv6Str(""), description="Cable modem IPv6 address when available.")
    ipv6_link_local: IPv6LinkLocalStr = Field(default=IPv6LinkLocalStr(IPv6Str("")), description="Cable modem IPv6 link-local address when available.")
    ds_channel_set: ChSetId = Field(default=ChSetId(0), description="Downstream channel set id when available.")
    us_channel_set: ChSetId = Field(default=ChSetId(0), description="Upstream channel set id when available.")
    registration_status: CmtsCmRegState = Field(default=CmtsCmRegState(0), description="Registration status when available.")


class ServiceGroupCableModemInventoryModel(BaseModel):
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier.")
    cm_count: int = Field(default=0, description="Number of registered cable modems for the service group.")
    cms: list[RegisteredCableModemModel] = Field(default_factory=list, description="Registered cable modems for the service group.")


class InventoryDiscoveryResultModel(BaseModel):
    cmts_host: HostNameStr = Field(default=HostNameStr(""), description="CMTS hostname or IP used for discovery.")
    discovered_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Discovered service group identifiers.")
    per_sg: list[ServiceGroupCableModemInventoryModel] = Field(default_factory=list, description="Registered cable modem inventory grouped by service group.")


__all__ = [
    "InventoryDiscoveryResultModel",
    "RegisteredCableModemModel",
    "ServiceGroupCableModemInventoryModel",
]

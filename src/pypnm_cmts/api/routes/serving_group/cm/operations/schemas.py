# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.docsis.data_type.sysDescr import SystemDescriptorModel
from pypnm.lib.mac_address import MacAddress, MacAddressFormat
from pypnm.lib.types import InetAddressStr, MacAddressStr

from pypnm_cmts.api.common.cmts_request import (
    CmtsServingGroupFilterModel,
    CmtsSnmpModel,
)
from pypnm_cmts.api.common.validation.request_normalization import RequestListNormalizer
from pypnm_cmts.api.routes.serving_group.operations.schemas import CacheResponseBase
from pypnm_cmts.lib.types import ServiceGroupId


class ServingGroupDocsDevResetNowCableModemModel(BaseModel):
    """Cable modem filter and SNMP override for docsDevResetNow."""

    mac_address: list[MacAddressStr] = Field(default_factory=list, description="Cable modem MAC addresses; empty means all.")
    snmp: CmtsSnmpModel | None = Field(default=None, description="Optional SNMP override parameters.")

    @model_validator(mode="after")
    def _normalize_macs(self) -> ServingGroupDocsDevResetNowCableModemModel:
        normalized: list[MacAddressStr] = []
        for mac in self.mac_address:
            try:
                normalized_mac = MacAddress(mac).to_mac_format(MacAddressFormat.COLON)
            except Exception as exc:
                raise ValueError("cable_modem.mac_address entries must be valid MAC addresses.") from exc
            normalized.append(MacAddressStr(str(normalized_mac)))
        self.mac_address = RequestListNormalizer.assert_unique_mac_addresses(
            normalized,
            "cable_modem.mac_address",
        )
        return self


class ServingGroupDocsDevResetNowEnvelopeModel(BaseModel):
    """CMTS envelope for docsDevResetNow requests."""

    serving_group: CmtsServingGroupFilterModel = Field(
        default_factory=CmtsServingGroupFilterModel,
        description="Serving group selection.",
    )
    cable_modem: ServingGroupDocsDevResetNowCableModemModel = Field(
        default_factory=ServingGroupDocsDevResetNowCableModemModel,
        description="Cable modem selection and SNMP overrides.",
    )


class ServingGroupDocsDevResetNowRequest(BaseModel):
    """Request model for SG-scoped docsDevResetNow cable modem reset."""

    model_config = ConfigDict(extra="ignore")

    cmts: ServingGroupDocsDevResetNowEnvelopeModel = Field(
        default_factory=ServingGroupDocsDevResetNowEnvelopeModel,
        description="CMTS request envelope.",
    )


class ServingGroupDocsDevResetNowResultModel(BaseModel):
    """Per-modem docsDevResetNow execution result."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    mac_address: MacAddressStr = Field(..., description="Cable modem MAC address.")
    ip_address: InetAddressStr | None = Field(default=None, description="Resolved cable modem IP address.")
    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Per-modem reset status code.")
    message: str = Field(default="", description="Per-modem reset status message.")


class ServingGroupDocsDevResetNowResponse(CacheResponseBase):
    """Response model for SG-scoped docsDevResetNow cable modem reset."""

    requested_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers.")
    requested_mac_addresses: list[MacAddressStr] = Field(default_factory=list, description="Requested cable modem MAC addresses.")
    resolved_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Resolved service group identifiers.")
    resolved_mac_addresses: list[MacAddressStr] = Field(default_factory=list, description="Resolved cable modem MAC addresses.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers not found.")
    missing_mac_addresses: list[MacAddressStr] = Field(
        default_factory=list,
        description="Requested cable modem MAC addresses not found in resolved scope.",
    )
    attempted_count: int = Field(default=0, ge=0, description="Total reset attempts issued.")
    success_count: int = Field(default=0, ge=0, description="Total successful reset commands.")
    failure_count: int = Field(default=0, ge=0, description="Total failed reset commands.")
    results: list[ServingGroupDocsDevResetNowResultModel] = Field(
        default_factory=list,
        description="Per-modem reset command results.",
    )


class ServingGroupCableModemSysDescrEntryModel(BaseModel):
    """Per-modem sysDescr payload."""

    sysdescr: SystemDescriptorModel = Field(
        default_factory=SystemDescriptorModel,
        description="Cable modem parsed sysDescr model.",
    )


class ServingGroupCableModemSysDescrGroupModel(BaseModel):
    """Per-serving-group sysDescr response payload."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Per-group status code.")
    message: str = Field(default="", description="Per-group status message.")
    modem_count: int = Field(default=0, ge=0, description="Resolved modem count in this serving group.")
    success_count: int = Field(default=0, ge=0, description="Modems with valid sysDescr values.")
    failure_count: int = Field(default=0, ge=0, description="Modems without valid sysDescr values.")
    modems: dict[MacAddressStr, ServingGroupCableModemSysDescrEntryModel] = Field(
        default_factory=dict,
        description="Per-modem sysDescr data keyed by cable modem MAC address.",
    )


class ServingGroupGetSysDescrResponse(CacheResponseBase):
    """Response model for SG-scoped cable modem sysDescr collection."""

    requested_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers.")
    requested_mac_addresses: list[MacAddressStr] = Field(default_factory=list, description="Requested cable modem MAC addresses.")
    resolved_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Resolved service group identifiers.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers not found.")
    missing_mac_addresses: list[MacAddressStr] = Field(
        default_factory=list,
        description="Requested cable modem MAC addresses not found in resolved scope.",
    )
    groups: list[ServingGroupCableModemSysDescrGroupModel] = Field(
        default_factory=list,
        description="Per-serving-group sysDescr results.",
    )


__all__ = [
    "ServingGroupDocsDevResetNowCableModemModel",
    "ServingGroupDocsDevResetNowEnvelopeModel",
    "ServingGroupDocsDevResetNowRequest",
    "ServingGroupDocsDevResetNowResponse",
    "ServingGroupDocsDevResetNowResultModel",
    "ServingGroupCableModemSysDescrEntryModel",
    "ServingGroupCableModemSysDescrGroupModel",
    "ServingGroupGetSysDescrResponse",
]

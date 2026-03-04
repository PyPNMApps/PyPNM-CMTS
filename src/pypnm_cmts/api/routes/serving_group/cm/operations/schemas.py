# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from enum import Enum

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
from pypnm_cmts.api.routes.serving_group.operations.schemas import (
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    MAX_REFRESH_TIMEOUT_SECONDS,
    CacheResponseBase,
)
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


class ServingGroupGetSysDescrCableModemModel(BaseModel):
    """Cable modem filter for getSysDescr."""

    mac_address: list[MacAddressStr] = Field(default_factory=list, description="Cable modem MAC addresses; empty means all.")

    @model_validator(mode="after")
    def _normalize_macs(self) -> ServingGroupGetSysDescrCableModemModel:
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


class ServingGroupGetSysDescrEnvelopeModel(BaseModel):
    """CMTS envelope for getSysDescr requests."""

    serving_group: CmtsServingGroupFilterModel = Field(
        default_factory=CmtsServingGroupFilterModel,
        description="Serving group selection.",
    )
    cable_modem: ServingGroupGetSysDescrCableModemModel = Field(
        default_factory=ServingGroupGetSysDescrCableModemModel,
        description="Cable modem selection.",
    )


class ServingGroupSysDescrPollSource(str, Enum):
    CACHE = "cache"
    HEAVY = "heavy"


class ServingGroupGetSysDescrPollModel(BaseModel):
    """Poll source selection and optional cache wait controls for getSysDescr."""

    source: ServingGroupSysDescrPollSource = Field(
        default=ServingGroupSysDescrPollSource.CACHE,
        description="Scope source selection: cache or heavy refresh.",
    )
    wait_for_cache: bool = Field(
        default=False,
        description="When source=heavy, wait for SGW cache snapshot advance before scope resolution.",
    )
    timeout_seconds: int = Field(
        default=DEFAULT_REFRESH_TIMEOUT_SECONDS,
        ge=1,
        le=MAX_REFRESH_TIMEOUT_SECONDS,
        description="Maximum seconds to wait when wait_for_cache is true.",
    )

    @model_validator(mode="after")
    def _normalize_wait(self) -> ServingGroupGetSysDescrPollModel:
        if self.source == ServingGroupSysDescrPollSource.CACHE:
            self.wait_for_cache = False
        return self


class ServingGroupGetSysDescrPollResultModel(BaseModel):
    """Poll type summary carried in getSysDescr responses."""

    type: ServingGroupSysDescrPollSource = Field(
        default=ServingGroupSysDescrPollSource.CACHE,
        description="Effective poll type used by this request.",
    )


class ServingGroupGetSysDescrRequest(BaseModel):
    """Request model for SG-scoped cable modem sysDescr collection."""

    model_config = ConfigDict(extra="ignore")

    cmts: ServingGroupGetSysDescrEnvelopeModel = Field(
        default_factory=ServingGroupGetSysDescrEnvelopeModel,
        description="CMTS request envelope.",
    )
    poll: ServingGroupGetSysDescrPollModel = Field(
        default_factory=ServingGroupGetSysDescrPollModel,
        description="Optional poll source controls.",
    )


class ServingGroupDocsDevResetNowModemModel(BaseModel):
    """Per-modem docsDevResetNow execution result."""

    ip_address: InetAddressStr | None = Field(default=None, description="Resolved cable modem IP address.")
    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Per-modem reset status code.")
    message: str = Field(default="", description="Per-modem reset status message.")
    ping_attempts: int = Field(default=0, ge=0, description="Number of post-reset ping verification attempts.")
    ping_last_reachable: bool | None = Field(default=None, description="Reachability observed on the last ping verification attempt.")


class ServingGroupDocsDevResetNowGroupModel(BaseModel):
    """Per-serving-group docsDevResetNow response payload."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Per-group status code.")
    message: str = Field(default="", description="Per-group status message.")
    modem_count: int = Field(default=0, ge=0, description="Resolved modem count in this serving group.")
    success_count: int = Field(default=0, ge=0, description="Modems reset and verified unreachable by ping.")
    failure_count: int = Field(default=0, ge=0, description="Modems where reset or ping verification failed.")
    modems: dict[MacAddressStr, ServingGroupDocsDevResetNowModemModel] = Field(
        default_factory=dict,
        description="Per-modem docsDevResetNow results keyed by cable modem MAC address.",
    )


class ServingGroupDocsDevResetNowResponse(CacheResponseBase):
    """Response model for SG-scoped docsDevResetNow cable modem reset."""

    requested_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers.")
    requested_mac_addresses: list[MacAddressStr] = Field(default_factory=list, description="Requested cable modem MAC addresses.")
    resolved_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Resolved service group identifiers.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers not found.")
    missing_mac_addresses: list[MacAddressStr] = Field(
        default_factory=list,
        description="Requested cable modem MAC addresses not found in resolved scope.",
    )
    groups: list[ServingGroupDocsDevResetNowGroupModel] = Field(
        default_factory=list,
        description="Per-serving-group docsDevResetNow results.",
    )


class ServingGroupCableModemSysDescrEntryModel(BaseModel):
    """Per-modem sysDescr payload."""

    sysdescr: SystemDescriptorModel = Field(
        default_factory=SystemDescriptorModel,
        description="Cable modem parsed sysDescr model.",
    )


class ServingGroupCableModemSysDescrGroupModel(BaseModel):
    """Per-serving-group sysDescr response payload."""

    service_group_id: ServiceGroupId = Field(..., description="Service group identifier.")
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

    poll: ServingGroupGetSysDescrPollResultModel = Field(
        default_factory=ServingGroupGetSysDescrPollResultModel,
        description="Effective poll type used by this response.",
    )
    groups: list[ServingGroupCableModemSysDescrGroupModel] = Field(
        default_factory=list,
        description="Per-serving-group sysDescr results.",
    )


__all__ = [
    "ServingGroupDocsDevResetNowCableModemModel",
    "ServingGroupDocsDevResetNowEnvelopeModel",
    "ServingGroupDocsDevResetNowRequest",
    "ServingGroupGetSysDescrCableModemModel",
    "ServingGroupGetSysDescrEnvelopeModel",
    "ServingGroupSysDescrPollSource",
    "ServingGroupGetSysDescrPollModel",
    "ServingGroupGetSysDescrPollResultModel",
    "ServingGroupGetSysDescrRequest",
    "ServingGroupDocsDevResetNowResponse",
    "ServingGroupDocsDevResetNowModemModel",
    "ServingGroupDocsDevResetNowGroupModel",
    "ServingGroupCableModemSysDescrEntryModel",
    "ServingGroupCableModemSysDescrGroupModel",
    "ServingGroupGetSysDescrResponse",
]

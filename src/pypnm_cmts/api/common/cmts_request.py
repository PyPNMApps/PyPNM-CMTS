# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from pypnm.lib.mac_address import MacAddress, MacAddressFormat
from pypnm.lib.types import (
    ChannelId,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    SnmpWriteCommunity,
)

from pypnm_cmts.api.common.validation.request_normalization import RequestListNormalizer
from pypnm_cmts.config.request_defaults import CmtsRequestDefaults
from pypnm_cmts.lib.types import ServiceGroupId


class CmtsServingGroupFilterModel(BaseModel):
    """Serving group filter for CMTS requests."""

    id: list[ServiceGroupId] = Field(
        default_factory=list,
        description="Serving group identifiers; empty means all.",
        json_schema_extra={"example": []},
    )

    @model_validator(mode="after")
    def _normalize_ids(self) -> CmtsServingGroupFilterModel:
        for sg_id in self.id:
            if int(sg_id) < 0:
                raise ValueError("serving_group.id values must be zero or greater.")
        self.id = RequestListNormalizer.assert_unique_service_group_ids(
            self.id,
            "serving_group.id",
        )
        return self


class CmtsTftpParametersModel(BaseModel):
    """TFTP override parameters for CMTS requests."""

    ipv4: IPv4Str | None = Field(..., description="Optional TFTP IPv4 override.")
    ipv6: IPv6Str | None = Field(..., description="Optional TFTP IPv6 override.")

    @field_validator("ipv4", "ipv6", mode="before")
    def _reject_blank_tftp(cls, v: object, info: ValidationInfo) -> object:
        if v is None:
            return v
        if isinstance(v, str) and v.strip() == "":
            raise ValueError(f"tftp.{info.field_name} must be null or a valid IP address")
        return v

    @model_validator(mode="after")
    def _require_keys_present(self) -> CmtsTftpParametersModel:
        if "ipv4" not in self.model_fields_set or "ipv6" not in self.model_fields_set:
            raise ValueError("tftp.ipv4 and tftp.ipv6 must be present (use null for defaults).")
        return self


class CmtsPnmCaptureParametersModel(BaseModel):
    """PNM capture override parameters for CMTS requests."""

    channel_ids: list[ChannelId] | None = Field(
        default=None,
        description="Optional channel id filter list; empty or missing means all channels.",
    )

    @model_validator(mode="after")
    def _normalize_channel_ids(self) -> CmtsPnmCaptureParametersModel:
        if not self.channel_ids:
            self.channel_ids = None
            return self
        self.channel_ids = RequestListNormalizer.assert_unique_channel_ids(
            self.channel_ids,
            "pnm_parameters.capture.channel_ids",
        )
        return self


class CmtsPnmParametersModel(BaseModel):
    """PNM override parameters for CMTS requests."""

    tftp: CmtsTftpParametersModel | None = Field(default=None, description="Optional TFTP override parameters.")
    capture: CmtsPnmCaptureParametersModel | None = Field(default=None, description="Optional capture override parameters.")


class CmtsSnmpV2CModel(BaseModel):
    """SNMPv2c override parameters for CMTS requests."""

    community: SnmpWriteCommunity | None = Field(
        ...,
        description="Optional SNMP write community override.",
    )

    @field_validator("community")
    def _reject_blank_community(cls, v: SnmpWriteCommunity | None) -> SnmpWriteCommunity | None:
        if v is None:
            return v
        if str(v).strip() == "":
            raise ValueError("snmpV2C.community must not be blank")
        return v

    @model_validator(mode="after")
    def _require_key_present(self) -> CmtsSnmpV2CModel:
        if "community" not in self.model_fields_set:
            raise ValueError("snmpV2C.community must be present (use null for defaults).")
        return self


class CmtsSnmpModel(BaseModel):
    """SNMP override parameters for CMTS requests."""

    snmpV2C: CmtsSnmpV2CModel | None = Field(default=None, description="Optional SNMPv2c override parameters.")


class CmtsCableModemFilterModel(BaseModel):
    """Cable modem filter and overrides for CMTS requests."""

    mac_address: list[MacAddressStr] = Field(default_factory=list, description="Cable modem MAC addresses; empty means all.")
    pnm_parameters: CmtsPnmParametersModel | None = Field(default=None, description="Optional PNM override parameters.")
    snmp: CmtsSnmpModel | None = Field(default=None, description="Optional SNMP override parameters.")

    @model_validator(mode="after")
    def _normalize_macs(self) -> CmtsCableModemFilterModel:
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


class CmtsRequestEnvelopeModel(BaseModel):
    """Canonical CMTS request envelope."""

    serving_group: CmtsServingGroupFilterModel = Field(default_factory=CmtsServingGroupFilterModel, description="Serving group selection.")
    cable_modem: CmtsCableModemFilterModel = Field(default_factory=CmtsCableModemFilterModel, description="Cable modem selection and overrides.")

    def resolve_sg_ids(self, discovered_sg_ids: list[ServiceGroupId]) -> list[ServiceGroupId]:
        """Return selected serving group ids using empty-list means all semantics."""
        sg: CmtsServingGroupFilterModel = self.serving_group
        if sg.id:
            return list(sg.id)
        return list(discovered_sg_ids)

    def resolve_mac_addresses(self, discovered_macs: list[MacAddressStr]) -> list[MacAddressStr]:
        """Return selected MAC addresses using empty-list means all semantics."""
        cm: CmtsCableModemFilterModel = self.cable_modem
        if cm.mac_address:
            return list(cm.mac_address)
        return list(discovered_macs)

    def apply_defaults(self, defaults: CmtsRequestDefaults) -> CmtsRequestEnvelopeModel:
        """Return a copy of the envelope with missing override defaults applied."""
        cable_modem = self.cable_modem
        snmp = cable_modem.snmp
        snmp_v2c = snmp.snmpV2C if snmp is not None else None
        write_community = snmp_v2c.community if snmp_v2c is not None else None
        if write_community is None and defaults.cm_snmpv2c_write_community is not None:
            snmp_v2c = (snmp_v2c or CmtsSnmpV2CModel(community=None)).model_copy(
                update={"community": defaults.cm_snmpv2c_write_community}
            )
            snmp = (snmp or CmtsSnmpModel()).model_copy(update={"snmpV2C": snmp_v2c})
            cable_modem = cable_modem.model_copy(update={"snmp": snmp})

        pnm = cable_modem.pnm_parameters
        tftp = pnm.tftp if pnm is not None else None
        ipv4_value = tftp.ipv4 if tftp is not None else None
        ipv6_value = tftp.ipv6 if tftp is not None else None
        if ipv4_value is None:
            ipv4_value = defaults.cm_tftp_ipv4
        if ipv6_value is None:
            ipv6_value = defaults.cm_tftp_ipv6
        if ipv4_value is not None or ipv6_value is not None:
            tftp = (tftp or CmtsTftpParametersModel(ipv4=None, ipv6=None)).model_copy(
                update={
                    "ipv4": ipv4_value,
                    "ipv6": ipv6_value,
                }
            )
            pnm = (pnm or CmtsPnmParametersModel()).model_copy(update={"tftp": tftp})
            cable_modem = cable_modem.model_copy(update={"pnm_parameters": pnm})

        return self.model_copy(update={"cable_modem": cable_modem})


class CmtsRequestModel(BaseModel):
    """Top-level CMTS request wrapper."""

    cmts: CmtsRequestEnvelopeModel = Field(default_factory=CmtsRequestEnvelopeModel, description="CMTS request envelope.")


__all__ = [
    "CmtsCableModemFilterModel",
    "CmtsPnmCaptureParametersModel",
    "CmtsPnmParametersModel",
    "CmtsRequestEnvelopeModel",
    "CmtsRequestModel",
    "CmtsServingGroupFilterModel",
    "CmtsSnmpModel",
    "CmtsSnmpV2CModel",
    "CmtsTftpParametersModel",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import pytest
from pydantic import ValidationError
from pypnm.lib.types import ChannelId, MacAddressStr

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsPnmCaptureParametersModel,
    CmtsRequestEnvelopeModel,
    CmtsServingGroupFilterModel,
    CmtsSnmpV2CModel,
    CmtsTftpParametersModel,
)
from pypnm_cmts.config.request_defaults import (
    ENV_CM_SNMPV2C_WRITE_COMMUNITY,
    ENV_CM_TFTP_IPV4,
    ENV_CM_TFTP_IPV6,
    CmtsRequestDefaults,
)
from pypnm_cmts.lib.types import ServiceGroupId


@pytest.mark.unit
def test_serving_group_filter_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="serving_group.id contains duplicate values"):
        CmtsServingGroupFilterModel(id=[ServiceGroupId(2), ServiceGroupId(1), ServiceGroupId(2)])


@pytest.mark.unit
def test_serving_group_filter_rejects_negative() -> None:
    with pytest.raises(ValidationError, match="serving_group.id values must be zero or greater."):
        CmtsServingGroupFilterModel(id=[ServiceGroupId(-1)])


@pytest.mark.unit
def test_cable_modem_filter_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="cable_modem.mac_address contains duplicate values"):
        CmtsCableModemFilterModel(
            mac_address=[
                MacAddressStr("aa:bb:cc:dd:ee:ff"),
                MacAddressStr("aa:bb:cc:dd:ee:ff"),
            ]
        )


@pytest.mark.unit
def test_cable_modem_filter_rejects_invalid_mac() -> None:
    with pytest.raises(ValidationError, match="cable_modem.mac_address entries must be valid MAC addresses."):
        CmtsCableModemFilterModel(mac_address=["invalid-mac"])


@pytest.mark.unit
def test_request_envelope_resolves_all_when_empty() -> None:
    envelope = CmtsRequestEnvelopeModel()
    discovered_sg_ids = [ServiceGroupId(1), ServiceGroupId(2)]
    discovered_macs = [
        MacAddressStr("aa:bb:cc:dd:ee:01"),
        MacAddressStr("aa:bb:cc:dd:ee:02"),
    ]
    assert envelope.resolve_sg_ids(discovered_sg_ids) == discovered_sg_ids
    assert envelope.resolve_mac_addresses(discovered_macs) == discovered_macs


@pytest.mark.unit
def test_request_envelope_resolves_selected() -> None:
    envelope = CmtsRequestEnvelopeModel(
        serving_group=CmtsServingGroupFilterModel(id=[ServiceGroupId(2)]),
        cable_modem=CmtsCableModemFilterModel(mac_address=[MacAddressStr("aa:bb:cc:dd:ee:ff")]),
    )
    discovered_sg_ids = [ServiceGroupId(1), ServiceGroupId(2)]
    discovered_macs = [MacAddressStr("aa:bb:cc:dd:ee:01")]
    assert envelope.resolve_sg_ids(discovered_sg_ids) == [ServiceGroupId(2)]
    assert envelope.resolve_mac_addresses(discovered_macs) == [MacAddressStr("aa:bb:cc:dd:ee:ff")]


@pytest.mark.unit
def test_request_apply_defaults_uses_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "private")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    defaults = CmtsRequestDefaults.from_system_config()
    envelope = CmtsRequestEnvelopeModel()
    applied = envelope.apply_defaults(defaults)

    snmp = applied.cable_modem.snmp
    assert snmp is not None
    assert snmp.snmpV2C is not None
    assert snmp.snmpV2C.community == "private"
    pnm = applied.cable_modem.pnm_parameters
    assert pnm is not None
    assert pnm.tftp is not None
    assert pnm.tftp.ipv4 == "192.168.0.100"
    assert pnm.tftp.ipv6 == "::1"


@pytest.mark.unit
def test_capture_channel_ids_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="pnm_parameters.capture.channel_ids contains duplicate values"):
        CmtsPnmCaptureParametersModel(channel_ids=[ChannelId(3), ChannelId(1), ChannelId(3)])


@pytest.mark.unit
def test_tftp_requires_ipv4_ipv6_keys() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        CmtsTftpParametersModel.model_validate({})


@pytest.mark.unit
def test_tftp_accepts_null_defaults() -> None:
    model = CmtsTftpParametersModel.model_validate({"ipv4": None, "ipv6": None})
    assert model.ipv4 is None
    assert model.ipv6 is None


@pytest.mark.unit
def test_tftp_rejects_blank_ipv4() -> None:
    with pytest.raises(ValidationError, match="tftp.ipv4 must be null or a valid IP address"):
        CmtsTftpParametersModel.model_validate({"ipv4": "", "ipv6": None})


@pytest.mark.unit
def test_snmpv2c_requires_community_key() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        CmtsSnmpV2CModel.model_validate({})


@pytest.mark.unit
def test_snmpv2c_accepts_null_default() -> None:
    model = CmtsSnmpV2CModel.model_validate({"community": None})
    assert model.community is None


@pytest.mark.unit
def test_snmpv2c_rejects_blank() -> None:
    with pytest.raises(ValidationError, match="snmpV2C.community must not be blank"):
        CmtsSnmpV2CModel.model_validate({"community": ""})


@pytest.mark.unit
def test_request_apply_defaults_preserves_capture() -> None:
    capture = CmtsPnmCaptureParametersModel(channel_ids=[ChannelId(33)])
    envelope = CmtsRequestEnvelopeModel(
        cable_modem=CmtsCableModemFilterModel(
            pnm_parameters={"capture": capture},
        )
    )
    defaults = CmtsRequestDefaults(
        cm_snmpv2c_write_community=None,
        cm_tftp_ipv4="192.168.0.100",
        cm_tftp_ipv6="::1",
    )
    applied = envelope.apply_defaults(defaults)
    pnm = applied.cable_modem.pnm_parameters
    assert pnm is not None
    assert pnm.capture is not None
    assert pnm.capture.channel_ids == [ChannelId(33)]

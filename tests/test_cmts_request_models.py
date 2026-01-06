# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest
from pypnm.lib.types import MacAddressStr

from pypnm_cmts.api.common.cmts_request import (
    CmtsCableModemFilterModel,
    CmtsRequestEnvelopeModel,
    CmtsServingGroupFilterModel,
)
from pypnm_cmts.config.request_defaults import (
    ENV_CM_SNMPV2C_WRITE_COMMUNITY,
    ENV_CM_TFTP_IPV4,
    ENV_CM_TFTP_IPV6,
    CmtsRequestDefaults,
)
from pypnm_cmts.lib.types import ServiceGroupId


@pytest.mark.unit
def test_serving_group_filter_dedupes_and_sorts() -> None:
    model = CmtsServingGroupFilterModel(id=[ServiceGroupId(2), ServiceGroupId(1), ServiceGroupId(2)])
    assert model.id == [ServiceGroupId(1), ServiceGroupId(2)]


@pytest.mark.unit
def test_serving_group_filter_rejects_negative() -> None:
    with pytest.raises(ValueError, match="serving_group.id values must be zero or greater."):
        CmtsServingGroupFilterModel(id=[ServiceGroupId(-1)])


@pytest.mark.unit
def test_cable_modem_filter_dedupes() -> None:
    model = CmtsCableModemFilterModel(
        mac_address=[
            MacAddressStr("aa:bb:cc:dd:ee:ff"),
            MacAddressStr("aa:bb:cc:dd:ee:ff"),
            MacAddressStr("aa:bb:cc:dd:ee:01"),
        ]
    )
    assert model.mac_address == [
        MacAddressStr("aa:bb:cc:dd:ee:ff"),
        MacAddressStr("aa:bb:cc:dd:ee:01"),
    ]


@pytest.mark.unit
def test_cable_modem_filter_rejects_invalid_mac() -> None:
    with pytest.raises(ValueError, match="cable_modem.mac_address entries must be valid MAC addresses."):
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

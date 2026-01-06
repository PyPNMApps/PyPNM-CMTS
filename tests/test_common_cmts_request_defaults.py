# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.api.routes.system.schemas import CmtsSysDescrRequest
from pypnm_cmts.config.request_defaults import (
    ENV_CM_SNMPV2C_WRITE_COMMUNITY,
    ENV_CM_TFTP_IPV4,
    ENV_CM_TFTP_IPV6,
)


@pytest.mark.unit
def test_common_cmts_request_applies_defaults_snake_case(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "private")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    payload = {
        "cmts": {
            "serving_group": {"id": []},
            "cable_modem": {"mac_address": []},
        },
        "target": {"hostname": "192.168.0.100"},
        "snmp": {"snmp_v2c": {"community": "public"}},
    }
    request = CmtsSysDescrRequest.model_validate(payload)
    snmp = request.cmts.cable_modem.snmp
    assert snmp is not None
    assert snmp.snmpV2C is not None
    assert snmp.snmpV2C.community == "private"
    tftp = request.cmts.cable_modem.pnm_parameters
    assert tftp is not None
    assert tftp.tftp is not None
    assert tftp.tftp.ipv4 == "192.168.0.100"
    assert tftp.tftp.ipv6 == "::1"


@pytest.mark.unit
def test_common_cmts_request_accepts_camelcase_snmp_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "private")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    payload = {
        "cmts": {
            "serving_group": {"id": []},
            "cable_modem": {"mac_address": []},
        },
        "target": {"hostname": "192.168.0.100"},
        "snmp": {"snmpV2c": {"community": "public"}},
    }
    request = CmtsSysDescrRequest.model_validate(payload)
    snmp = request.cmts.cable_modem.snmp
    assert snmp is not None
    assert snmp.snmpV2C is not None
    assert snmp.snmpV2C.community == "private"


@pytest.mark.unit
def test_common_cmts_request_keeps_explicit_snmp_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "private")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.100")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::1")

    payload = {
        "cmts": {
            "serving_group": {"id": []},
            "cable_modem": {
                "mac_address": [],
                "snmp": {"snmpV2C": {"community": "explicit-write"}},
            },
        },
        "target": {"hostname": "192.168.0.100"},
        "snmp": {"snmpV2c": {"community": "public"}},
    }
    request = CmtsSysDescrRequest.model_validate(payload)
    snmp = request.cmts.cable_modem.snmp
    assert snmp is not None
    assert snmp.snmpV2C is not None
    assert snmp.snmpV2C.community == "explicit-write"


@pytest.mark.unit
def test_common_cmts_request_keeps_explicit_tftp_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CM_SNMPV2C_WRITE_COMMUNITY, "private")
    monkeypatch.setenv(ENV_CM_TFTP_IPV4, "192.168.0.101")
    monkeypatch.setenv(ENV_CM_TFTP_IPV6, "::2")

    payload = {
        "cmts": {
            "serving_group": {"id": []},
            "cable_modem": {
                "mac_address": [],
                "pnm_parameters": {
                    "tftp": {
                        "ipv4": "192.168.0.100",
                        "ipv6": "::1",
                    }
                },
            },
        },
        "target": {"hostname": "192.168.0.100"},
        "snmp": {"snmpV2c": {"community": "public"}},
    }
    request = CmtsSysDescrRequest.model_validate(payload)
    tftp = request.cmts.cable_modem.pnm_parameters
    assert tftp is not None
    assert tftp.tftp is not None
    assert tftp.tftp.ipv4 == "192.168.0.100"
    assert tftp.tftp.ipv6 == "::1"

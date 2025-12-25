# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

from pypnm.config.config_manager import ConfigManager

from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings


def _write_system_config(path: Path) -> None:
    config = {
        "pypnm-cmts": {
            "cmts": [
                {
                    "device": {
                        "hostname": "cmts-01",
                        "model": "CBR8",
                        "vendor": "Cisco",
                    },
                    "SNMP": {
                        "timeouts": {
                            "request_seconds": 7,
                            "retries": 2,
                        },
                        "version": {
                            "2c": {
                                "port": 161,
                                "enable": True,
                                "read_community": "public",
                                "retries": 4,
                                "write_community": "private",
                            },
                            "3": {
                                "enable": True,
                                "port": 161,
                                "authPassword": "auth-pass",
                                "authProtocol": "SHA",
                                "privPassword": "priv-pass",
                                "privProtocol": "AES",
                                "retries": 3,
                                "securityLevel": "authPriv",
                                "username": "snmp-user",
                            },
                        },
                    },
                }
            ]
        }
    }
    path.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")


def test_cmts_system_config_settings_reads_cmts_values(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    original_cfg = CmtsSystemConfigSettings._cfg
    CmtsSystemConfigSettings._cfg = ConfigManager(config_path=str(config_path))

    try:
        assert CmtsSystemConfigSettings.cmts_count() == 1
        assert CmtsSystemConfigSettings.cmts_device_hostname(0) == "cmts-01"
        assert CmtsSystemConfigSettings.cmts_device_model(0) == "CBR8"
        assert CmtsSystemConfigSettings.cmts_device_vendor(0) == "Cisco"

        assert CmtsSystemConfigSettings.cmts_snmp_timeout_seconds(0) == 7
        assert CmtsSystemConfigSettings.cmts_snmp_timeout_retries(0) == 2

        assert CmtsSystemConfigSettings.cmts_snmp_v2c_enabled(0) is True
        assert CmtsSystemConfigSettings.cmts_snmp_v2c_port(0) == 161
        assert CmtsSystemConfigSettings.cmts_snmp_v2c_read_community(0) == "public"
        assert CmtsSystemConfigSettings.cmts_snmp_v2c_write_community(0) == "private"
        assert CmtsSystemConfigSettings.cmts_snmp_v2c_retries(0) == 4

        assert CmtsSystemConfigSettings.cmts_snmp_v3_enabled(0) is True
        assert CmtsSystemConfigSettings.cmts_snmp_v3_port(0) == 161
        assert CmtsSystemConfigSettings.cmts_snmp_v3_username(0) == "snmp-user"
        assert CmtsSystemConfigSettings.cmts_snmp_v3_security_level(0) == "authPriv"
        assert CmtsSystemConfigSettings.cmts_snmp_v3_auth_protocol(0) == "SHA"
        assert CmtsSystemConfigSettings.cmts_snmp_v3_auth_password(0) == "auth-pass"
        assert CmtsSystemConfigSettings.cmts_snmp_v3_priv_protocol(0) == "AES"
        assert CmtsSystemConfigSettings.cmts_snmp_v3_priv_password(0) == "priv-pass"
        assert CmtsSystemConfigSettings.cmts_snmp_v3_retries(0) == 3
    finally:
        CmtsSystemConfigSettings._cfg = original_cfg

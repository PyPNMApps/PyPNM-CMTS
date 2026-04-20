# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

"""System configuration settings placeholder for PyPNM-CMTS."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from pypnm.config.system_config_settings import SystemConfigSettings
from pypnm.lib.types import HostNameStr


class CmtsSystemConfigSettings(SystemConfigSettings):
    """System configuration settings for PyPNM-CMTS."""

    _CMTS_ROOT_KEY: str = "pypnm-cmts"
    _CMTS_LIST_KEY: str = "cmts"
    _CMTS_SERVICE_KEY: str = "service"
    _CMTS_WEB_SERVICE_KEY: str = "webService"

    _CMTS_DEVICE_KEY: str = "device"
    _CMTS_SNMP_KEY: str = "SNMP"
    _CMTS_SNMP_TIMEOUTS_KEY: str = "timeouts"
    _CMTS_SNMP_VERSION_KEY: str = "version"
    _CMTS_SNMP_V2_KEY: str = "2c"
    _CMTS_SNMP_V3_KEY: str = "3"

    _DEFAULT_CMTS_SNMP_PORT: int = 161
    _DEFAULT_CMTS_SNMP_RETRIES: int = 3
    _DEFAULT_CMTS_SNMP_TIMEOUT: int = 5
    _DEFAULT_CMTS_SNMP_V3_USERNAME: str = "user"
    _DEFAULT_CMTS_SNMP_V3_AUTH_PROTOCOL: str = "SHA"
    _DEFAULT_CMTS_SNMP_V3_PRIV_PROTOCOL: str = "AES"
    _DEFAULT_CMTS_SNMP_V3_SECURITY_LEVEL: str = "authPriv"
    _DEFAULT_WEB_SERVICE_MEMORY_GUARD_ENABLED: bool = True
    _DEFAULT_WEB_SERVICE_MEMORY_GUARD_RSS_RESTART_THRESHOLD_MB: int = 1536
    _DEFAULT_WEB_SERVICE_MEMORY_GUARD_POLL_SECONDS: int = 10
    _DEFAULT_WEB_SERVICE_MEMORY_GUARD_MIN_RESTART_INTERVAL_SECONDS: int = 300
    _DEFAULT_WEB_SERVICE_MEMORY_GUARD_MAX_RESTARTS_PER_HOUR: int = 6

    @classmethod
    def _cmts_entries(cls) -> list[dict[str, object]]:
        entries = cls._cfg.get(cls._CMTS_ROOT_KEY, cls._CMTS_LIST_KEY)
        if entries is None:
            return []
        if not isinstance(entries, list):
            cls._logger.error(
                "Invalid configuration value for '%s.%s'; expected list",
                cls._CMTS_ROOT_KEY,
                cls._CMTS_LIST_KEY,
            )
            return []
        return [entry for entry in entries if isinstance(entry, dict)]

    @classmethod
    def _cmts_entry(cls, index: int) -> dict[str, object]:
        entries = cls._cmts_entries()
        if not entries:
            return {}
        if index < 0 or index >= len(entries):
            cls._logger.error(
                "CMTS entry index %d out of range (entries=%d)",
                index,
                len(entries),
            )
            return {}
        return entries[index]

    @classmethod
    def _get_nested_value(cls, data: dict[str, object], *path: str) -> object | None:
        current: object = data
        for key in path:
            if not isinstance(current, dict):
                return None
            if key not in current:
                return None
            current = current[key]
        return current

    @classmethod
    def _get_nested_str(cls, default: str, data: dict[str, object], *path: str) -> str:
        value = cls._get_nested_value(data, *path)
        if value is None:
            return default
        if isinstance(value, str):
            if value == "":
                return default
            return value
        return str(value)

    @classmethod
    def _get_nested_int(cls, default: int, data: dict[str, object], *path: str) -> int:
        value = cls._get_nested_value(data, *path)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _get_nested_bool(cls, default: bool, data: dict[str, object], *path: str) -> bool:
        value = cls._get_nested_value(data, *path)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
        return default

    @classmethod
    def cmts_count(cls) -> int:
        """Return the number of CMTS entries in the system configuration."""
        return len(cls._cmts_entries())

    @classmethod
    def cmts_device_hostname(cls, index: int) -> HostNameStr:
        """Return the CMTS hostname for the selected entry."""
        entry = cls._cmts_entry(index)
        hostname = cls._get_nested_str("", entry, cls._CMTS_DEVICE_KEY, "hostname")
        return cast(HostNameStr, hostname)

    @classmethod
    def cmts_device_model(cls, index: int) -> str:
        """Return the CMTS model for the selected entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str("", entry, cls._CMTS_DEVICE_KEY, "model")

    @classmethod
    def cmts_device_vendor(cls, index: int) -> str:
        """Return the CMTS vendor for the selected entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str("", entry, cls._CMTS_DEVICE_KEY, "vendor")

    @classmethod
    def cmts_snmp_timeout_seconds(cls, index: int) -> int:
        """Return the CMTS SNMP request timeout in seconds."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_int(
            cls._DEFAULT_CMTS_SNMP_TIMEOUT,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_TIMEOUTS_KEY,
            "request_seconds",
        )

    @classmethod
    def cmts_snmp_timeout_retries(cls, index: int) -> int:
        """Return the CMTS SNMP retry count from the timeout section."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_int(
            cls._DEFAULT_CMTS_SNMP_RETRIES,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_TIMEOUTS_KEY,
            "retries",
        )

    @classmethod
    def cmts_snmp_v2c_enabled(cls, index: int) -> bool:
        """Return whether SNMPv2c is enabled for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_bool(
            True,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V2_KEY,
            "enable",
        )

    @classmethod
    def cmts_snmp_v2c_port(cls, index: int) -> int:
        """Return the SNMPv2c port for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_int(
            cls._DEFAULT_CMTS_SNMP_PORT,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V2_KEY,
            "port",
        )

    @classmethod
    def cmts_snmp_v2c_read_community(cls, index: int) -> str:
        """Return the SNMPv2c read community for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str(
            "",
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V2_KEY,
            "read_community",
        )

    @classmethod
    def cmts_snmp_v2c_write_community(cls, index: int) -> str:
        """Return the SNMPv2c write community for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str(
            "",
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V2_KEY,
            "write_community",
        )

    @classmethod
    def cmts_snmp_v2c_retries(cls, index: int) -> int:
        """Return the SNMPv2c retry count for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_int(
            cls._DEFAULT_CMTS_SNMP_RETRIES,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V2_KEY,
            "retries",
        )

    @classmethod
    def cmts_snmp_v3_enabled(cls, index: int) -> bool:
        """Return whether SNMPv3 is enabled for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_bool(
            False,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "enable",
        )

    @classmethod
    def cmts_snmp_v3_port(cls, index: int) -> int:
        """Return the SNMPv3 port for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_int(
            cls._DEFAULT_CMTS_SNMP_PORT,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "port",
        )

    @classmethod
    def cmts_snmp_v3_username(cls, index: int) -> str:
        """Return the SNMPv3 username for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str(
            cls._DEFAULT_CMTS_SNMP_V3_USERNAME,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "username",
        )

    @classmethod
    def web_service_reload_sentinel_path(cls) -> Path:
        """Return the configured web-service reload sentinel path."""
        configured_path = cls._get_nested_str(
            "",
            cls._cfg.get(cls._CMTS_ROOT_KEY) or {},
            cls._CMTS_SERVICE_KEY,
            cls._CMTS_WEB_SERVICE_KEY,
            "reloadSentinelPath",
        )
        if configured_path.strip() != "":
            return Path(configured_path).expanduser()
        return cls.coordination_state_dir() / "webservice.reload"

    @classmethod
    def web_service_memory_guard_enabled(cls) -> bool:
        """Return whether the web-service RSS guard is enabled."""
        return cls._get_nested_bool(
            cls._DEFAULT_WEB_SERVICE_MEMORY_GUARD_ENABLED,
            cls._cfg.get(cls._CMTS_ROOT_KEY) or {},
            cls._CMTS_SERVICE_KEY,
            cls._CMTS_WEB_SERVICE_KEY,
            "memoryGuard",
            "enabled",
        )

    @classmethod
    def web_service_memory_guard_rss_restart_threshold_mb(cls) -> int:
        """Return the RSS threshold in MiB for web-service reload requests."""
        return cls._get_nested_int(
            cls._DEFAULT_WEB_SERVICE_MEMORY_GUARD_RSS_RESTART_THRESHOLD_MB,
            cls._cfg.get(cls._CMTS_ROOT_KEY) or {},
            cls._CMTS_SERVICE_KEY,
            cls._CMTS_WEB_SERVICE_KEY,
            "memoryGuard",
            "rssRestartThresholdMb",
        )

    @classmethod
    def web_service_memory_guard_poll_seconds(cls) -> int:
        """Return the polling interval for the web-service RSS guard."""
        return cls._get_nested_int(
            cls._DEFAULT_WEB_SERVICE_MEMORY_GUARD_POLL_SECONDS,
            cls._cfg.get(cls._CMTS_ROOT_KEY) or {},
            cls._CMTS_SERVICE_KEY,
            cls._CMTS_WEB_SERVICE_KEY,
            "memoryGuard",
            "pollSeconds",
        )

    @classmethod
    def web_service_memory_guard_min_restart_interval_seconds(cls) -> int:
        """Return the minimum seconds between web-service guard reload requests."""
        return cls._get_nested_int(
            cls._DEFAULT_WEB_SERVICE_MEMORY_GUARD_MIN_RESTART_INTERVAL_SECONDS,
            cls._cfg.get(cls._CMTS_ROOT_KEY) or {},
            cls._CMTS_SERVICE_KEY,
            cls._CMTS_WEB_SERVICE_KEY,
            "memoryGuard",
            "minRestartIntervalSeconds",
        )

    @classmethod
    def web_service_memory_guard_max_restarts_per_hour(cls) -> int:
        """Return the maximum web-service guard reload requests allowed per hour."""
        return cls._get_nested_int(
            cls._DEFAULT_WEB_SERVICE_MEMORY_GUARD_MAX_RESTARTS_PER_HOUR,
            cls._cfg.get(cls._CMTS_ROOT_KEY) or {},
            cls._CMTS_SERVICE_KEY,
            cls._CMTS_WEB_SERVICE_KEY,
            "memoryGuard",
            "maxRestartsPerHour",
        )

    @classmethod
    def cmts_snmp_v3_security_level(cls, index: int) -> str:
        """Return the SNMPv3 security level for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str(
            cls._DEFAULT_CMTS_SNMP_V3_SECURITY_LEVEL,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "securityLevel",
        )

    @classmethod
    def cmts_snmp_v3_auth_protocol(cls, index: int) -> str:
        """Return the SNMPv3 auth protocol for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str(
            cls._DEFAULT_CMTS_SNMP_V3_AUTH_PROTOCOL,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "authProtocol",
        )

    @classmethod
    def cmts_snmp_v3_auth_password(cls, index: int) -> str:
        """Return the SNMPv3 auth password for the CMTS entry."""
        entry = cls._cmts_entry(index)
        value = cls._get_nested_str(
            "",
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "authPassword",
        )
        return cls._maybe_decrypt(
            value,
            cls._CMTS_ROOT_KEY,
            cls._CMTS_LIST_KEY,
            str(index),
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "authPassword",
        )

    @classmethod
    def cmts_snmp_v3_priv_protocol(cls, index: int) -> str:
        """Return the SNMPv3 privacy protocol for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_str(
            cls._DEFAULT_CMTS_SNMP_V3_PRIV_PROTOCOL,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "privProtocol",
        )

    @classmethod
    def cmts_snmp_v3_priv_password(cls, index: int) -> str:
        """Return the SNMPv3 privacy password for the CMTS entry."""
        entry = cls._cmts_entry(index)
        value = cls._get_nested_str(
            "",
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "privPassword",
        )
        return cls._maybe_decrypt(
            value,
            cls._CMTS_ROOT_KEY,
            cls._CMTS_LIST_KEY,
            str(index),
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "privPassword",
        )

    @classmethod
    def cmts_snmp_v3_retries(cls, index: int) -> int:
        """Return the SNMPv3 retry count for the CMTS entry."""
        entry = cls._cmts_entry(index)
        return cls._get_nested_int(
            cls._DEFAULT_CMTS_SNMP_RETRIES,
            entry,
            cls._CMTS_SNMP_KEY,
            cls._CMTS_SNMP_VERSION_KEY,
            cls._CMTS_SNMP_V3_KEY,
            "retries",
        )

    @classmethod
    def data_root_dir(cls) -> Path:
        """Return the configured PyPNM data root directory."""
        return Path(cls.pnm_dir()).parent

    @classmethod
    def coordination_state_dir(cls) -> Path:
        """Return the CMTS coordination state directory."""
        return cls.data_root_dir() / "coordination"

    @classmethod
    def sg_operations_dir(cls) -> Path:
        """Return the CMTS SG operations directory derived from the configured PNM data root."""
        return cls.data_root_dir() / "sg_operations"

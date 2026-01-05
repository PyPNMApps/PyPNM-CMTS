# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os

import pytest

ENV_LIVE_ENABLED = "PYPNM_CMTS_RUN_LIVE"
ENV_LIVE_HOSTNAME = "PYPNM_CMTS_LIVE_HOSTNAME"
ENV_LIVE_COMMUNITY = "PYPNM_CMTS_LIVE_SNMP_COMMUNITY"
ENV_LIVE_PORT = "PYPNM_CMTS_LIVE_SNMP_PORT"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live CMTS tests (requires PYPNM_CMTS_LIVE_HOSTNAME and PYPNM_CMTS_LIVE_SNMP_COMMUNITY).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: live CMTS tests (enable with --run-live or PYPNM_CMTS_RUN_LIVE=1)",
    )
    if _live_enabled(config):
        _validate_live_env()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _live_enabled(config):
        return
    skip_marker = pytest.mark.skip(
        reason="live CMTS tests require --run-live or PYPNM_CMTS_RUN_LIVE=1",
    )
    for item in items:
        if "live" in item.keywords or "live_cmts" in item.keywords:
            item.add_marker(skip_marker)


def _live_enabled(config: pytest.Config) -> bool:
    if bool(config.getoption("--run-live")):
        return True
    return os.environ.get(ENV_LIVE_ENABLED) == "1"


def _validate_live_env() -> None:
    hostname = os.environ.get(ENV_LIVE_HOSTNAME, "").strip()
    community = os.environ.get(ENV_LIVE_COMMUNITY, "").strip()
    if hostname == "":
        raise pytest.UsageError("PYPNM_CMTS_LIVE_HOSTNAME is required when live tests are enabled.")
    if community == "":
        raise pytest.UsageError("PYPNM_CMTS_LIVE_SNMP_COMMUNITY is required when live tests are enabled.")
    port_value = os.environ.get(ENV_LIVE_PORT, "").strip()
    if port_value == "":
        return
    try:
        if int(port_value) <= 0:
            raise ValueError
    except ValueError as exc:
        raise pytest.UsageError("PYPNM_CMTS_LIVE_SNMP_PORT must be a positive integer.") from exc


__all__ = [
    "ENV_LIVE_COMMUNITY",
    "ENV_LIVE_ENABLED",
    "ENV_LIVE_HOSTNAME",
    "ENV_LIVE_PORT",
]

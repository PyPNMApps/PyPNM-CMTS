# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)


def _adapter_payload() -> dict[str, object]:
    return {"adapter": {"hostname": "cmts.example", "community": "public"}}


def test_sgw_settings_defaults() -> None:
    settings = CmtsOrchestratorSettings.model_validate(_adapter_payload())
    sgw = settings.sgw
    assert sgw.enabled is True
    assert int(sgw.poll_light_seconds) == 300
    assert int(sgw.poll_heavy_seconds) == 900
    assert int(sgw.refresh_jitter_seconds) == 30
    assert int(sgw.cache_max_age_seconds) == 1200
    assert int(sgw.max_workers) == 0
    assert sgw.discovery.mode == "snmp"


def test_sgw_settings_rejects_non_positive_light_poll() -> None:
    with pytest.raises(ValueError, match="sgw.poll_light_seconds must be greater than zero."):
        CmtsOrchestratorSettings.model_validate(
            {**_adapter_payload(), "sgw": {"poll_light_seconds": 0}}
        )


def test_sgw_settings_rejects_heavy_less_than_light() -> None:
    with pytest.raises(ValueError, match="sgw.poll_heavy_seconds must be greater than or equal to sgw.poll_light_seconds."):
        CmtsOrchestratorSettings.model_validate(
            {**_adapter_payload(), "sgw": {"poll_light_seconds": 300, "poll_heavy_seconds": 60}}
        )


def test_sgw_settings_rejects_excessive_jitter() -> None:
    with pytest.raises(ValueError, match="sgw.refresh_jitter_seconds must be less than or equal to sgw.poll_light_seconds."):
        CmtsOrchestratorSettings.model_validate(
            {**_adapter_payload(), "sgw": {"poll_light_seconds": 300, "refresh_jitter_seconds": 301}}
        )


def test_sgw_settings_rejects_negative_max_workers() -> None:
    with pytest.raises(ValueError, match="sgw.max_workers must be non-negative."):
        CmtsOrchestratorSettings.model_validate(
            {**_adapter_payload(), "sgw": {"max_workers": -1}}
        )


def test_sgw_settings_rejects_invalid_discovery_mode() -> None:
    with pytest.raises(ValueError, match="sgw.discovery.mode must be 'static' or 'snmp'."):
        CmtsOrchestratorSettings.model_validate(
            {**_adapter_payload(), "sgw": {"discovery": {"mode": "invalid"}}}
        )


def test_sgw_settings_snmp_requires_hostname_and_community() -> None:
    base_payload = {
        "sgw": {"discovery": {"mode": "snmp"}},
        "adapter": {
            "hostname": "cmts.example",
            "community": "public",
        },
    }
    with pytest.raises(ValueError, match="adapter.hostname must be set for snmp discovery."):
        CmtsOrchestratorSettings.model_validate(
            {
                **base_payload,
                "adapter": {"hostname": "", "community": "public"},
            }
        )
    with pytest.raises(ValueError, match="adapter.community must be set for snmp discovery."):
        CmtsOrchestratorSettings.model_validate(
            {
                **base_payload,
                "adapter": {"hostname": "cmts.example", "community": ""},
            }
        )
    settings = CmtsOrchestratorSettings.model_validate(base_payload)
    assert settings.sgw.discovery.mode == "snmp"


def test_sgw_settings_rejects_small_cache_max_age() -> None:
    with pytest.raises(ValueError, match="sgw.cache_max_age_seconds must be greater than or equal to sgw.poll_light_seconds."):
        CmtsOrchestratorSettings.model_validate(
            {**_adapter_payload(), "sgw": {"poll_light_seconds": 300, "cache_max_age_seconds": 200}}
        )


def test_sgw_settings_accepts_poll_heavy_equal_to_light() -> None:
    poll_seconds = 300
    settings = CmtsOrchestratorSettings.model_validate(
        {**_adapter_payload(), "sgw": {"poll_light_seconds": poll_seconds, "poll_heavy_seconds": poll_seconds}}
    )
    assert int(settings.sgw.poll_heavy_seconds) == poll_seconds


def test_sgw_settings_accepts_max_jitter_equal_to_light() -> None:
    poll_seconds = 300
    settings = CmtsOrchestratorSettings.model_validate(
        {**_adapter_payload(), "sgw": {"poll_light_seconds": poll_seconds, "refresh_jitter_seconds": poll_seconds}}
    )
    assert int(settings.sgw.refresh_jitter_seconds) == poll_seconds


def test_sgw_settings_accepts_zero_jitter() -> None:
    poll_seconds = 300
    jitter_seconds = 0
    settings = CmtsOrchestratorSettings.model_validate(
        {**_adapter_payload(), "sgw": {"poll_light_seconds": poll_seconds, "refresh_jitter_seconds": jitter_seconds}}
    )
    assert int(settings.sgw.refresh_jitter_seconds) == jitter_seconds


def test_sgw_settings_accepts_cache_max_age_equal_to_light() -> None:
    poll_seconds = 300
    settings = CmtsOrchestratorSettings.model_validate(
        {**_adapter_payload(), "sgw": {"poll_light_seconds": poll_seconds, "cache_max_age_seconds": poll_seconds}}
    )
    assert int(settings.sgw.cache_max_age_seconds) == poll_seconds


def test_sgw_cache_metadata_refresh_state_values() -> None:
    for value in (SgwRefreshState.OK, SgwRefreshState.STALE, SgwRefreshState.ERROR):
        model = SgwCacheMetadataModel(refresh_state=value)
        assert model.refresh_state == value

    for value in ("OK", "STALE", "ERROR"):
        model = SgwCacheMetadataModel(refresh_state=value)
        assert model.refresh_state.value == value


def test_sgw_cache_metadata_rejects_long_error() -> None:
    too_long = "a" * (SGW_LAST_ERROR_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        SgwCacheMetadataModel(last_error=too_long)

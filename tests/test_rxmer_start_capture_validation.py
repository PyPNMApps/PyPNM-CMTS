# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pypnm.lib.types import ChannelId, IPv4Str, IPv6Str, MacAddressStr

from pypnm_cmts.api.main import app
from pypnm_cmts.lib.constants import RfChannelType
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwRfChannelModel,
    SgwSnapshotModel,
)
from pypnm_cmts.sgw.runtime_state import reset_sgw_runtime_state
from pypnm_cmts.sgw.store import SgwCacheStore


async def _noop() -> None:
    return


def _build_runtime_store() -> SgwCacheStore:
    store = SgwCacheStore()
    snapshot = SgwSnapshotModel(
        sg_id=ServiceGroupId(1),
        cable_modems=[
            SgwCableModemModel(
                mac=MacAddressStr("aa:bb:cc:dd:ee:00"),
                ipv4=IPv4Str("192.168.0.100"),
                ipv6=IPv6Str(""),
            )
        ],
        ds_rf_channels=[
            SgwRfChannelModel(
                channel_id=int(ChannelId(100)),
                channel_type=RfChannelType.OFDM,
            )
        ],
    )
    store.upsert_entry(SgwCacheEntryModel(sg_id=ServiceGroupId(1), snapshot=snapshot))
    return store


@pytest.mark.unit
def test_rxmer_start_capture_rejects_invalid_channel_id(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    monkeypatch.setattr("pypnm_cmts.api.main._sgw_startup_service.initialize", _noop)
    runtime_store = _build_runtime_store()
    monkeypatch.setattr(
        "pypnm_cmts.api.common.service.pnm.scope.PnmOperationScopeResolver.resolve_store",
        lambda _self: runtime_store,
    )

    payload = {
        "cmts": {
            "serving_group": {"id": [1]},
            "cable_modem": {
                "mac_address": ["aa:bb:cc:dd:ee:00"],
                "pnm_parameters": {
                    "capture": {
                        "channel_ids": [999],
                    }
                },
            },
        },
        "execution": {
            "max_workers": 1,
            "retry_count": 0,
            "retry_delay_seconds": 0.0,
            "per_modem_timeout_seconds": 1.0,
            "overall_timeout_seconds": 2.0,
        },
    }

    with TestClient(app) as client:
        response = client.post("/cmts/pnm/sg/ds/ofdm/rxmer/startCapture", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "invalid downstream OFDM channel ids" in detail
    assert "999" in detail
    assert "100" in detail

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel, SgwHeavyInventoryModel
from pypnm_cmts.sgw.pollers.heavy import HeavyInventoryProvider, sgw_heavy_poller


class FakeInventoryProvider:
    """Fake provider with unordered and duplicated inventory."""

    def fetch_inventory(
        self,
        _sg_id: ServiceGroupId,
        _settings: CmtsOrchestratorSettings,
    ) -> SgwHeavyInventoryModel:
        return SgwHeavyInventoryModel(
            ds_channel_ids=[3, 1, 3, 2, 0, -1],
            us_channel_ids=[5, 4, 4, 0],
            cable_modems=[
                SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.2", ipv6=""),
                SgwCableModemModel(mac="aa:bb:cc:dd:ee:01", ipv4="192.168.0.1", ipv6=""),
                SgwCableModemModel(mac="aa:bb:cc:dd:ee:ff", ipv4="192.168.0.2", ipv6=""),
            ],
        )


@pytest.mark.unit
def test_sgw_heavy_poller_orders_inventory() -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {
            "adapter": {
                "hostname": "cmts.example",
                "community": "public",
                "write_community": "private",
                "port": 161,
            }
        }
    )
    provider: HeavyInventoryProvider = FakeInventoryProvider()

    payload = sgw_heavy_poller(ServiceGroupId(1), settings, provider=provider)

    assert payload.ds_channels.channel_ids == [1, 2, 3]
    assert payload.ds_channels.count == 3
    assert payload.us_channels.channel_ids == [4, 5]
    assert payload.us_channels.count == 2
    assert [str(modem.mac) for modem in payload.cable_modems] == [
        "aa:bb:cc:dd:ee:01",
        "aa:bb:cc:dd:ee:ff",
    ]

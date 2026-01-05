# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import threading
import time

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.store import SgwCacheStore


@pytest.mark.unit
def test_sgw_manager_stop_unblocks_wait() -> None:
    store = SgwCacheStore()
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    settings.sgw.poll_light_seconds = 5.0
    manager = SgwManager(settings=settings, store=store, service_groups=[ServiceGroupId(1)])

    thread = threading.Thread(target=manager.refresh_forever, daemon=True)
    thread.start()
    time.sleep(0.01)

    start = time.monotonic()
    manager.stop()
    thread.join(timeout=1.0)
    duration = time.monotonic() - start

    assert not thread.is_alive()
    assert duration < 1.0

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from __future__ import annotations

import threading

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.store import SgwCacheStore


@pytest.mark.unit
def test_sgw_manager_stop_before_start_unblocks_immediately() -> None:
    """
    Ensure that if `stop()` is called before `refresh_forever()` starts,
    the manager does not clear the stop event and will not start a long-running loop.
    """
    store = SgwCacheStore()
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    # Make the sleep interval long to detect blocking if stop-not-respected
    settings.sgw.poll_light_seconds = 5.0
    manager = SgwManager(settings=settings, store=store, service_groups=[ServiceGroupId(1)])

    # Request stop before starting the thread
    manager.stop()

    thread = threading.Thread(target=manager.refresh_forever, daemon=True)
    thread.start()

    # Allow a sliver of time for thread to run/exit
    thread.join(timeout=1.0)

    assert not thread.is_alive()

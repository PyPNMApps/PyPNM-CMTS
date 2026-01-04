# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.pollers.heavy import sgw_heavy_poller
from pypnm_cmts.sgw.pollers.light import sgw_light_poller
from pypnm_cmts.sgw.runtime_state import (
    compute_sgw_cache_ready,
    set_sgw_startup_failure,
    set_sgw_startup_prime_failure,
    set_sgw_startup_success,
    start_sgw_background_refresh,
)
from pypnm_cmts.sgw.store import SgwCacheStore


class SgwStartupService:
    """Service for SG discovery and SGW priming at startup."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    async def initialize(self) -> None:
        """
        Discover SGs and prime SGW cache at startup.
        """
        settings = CmtsOrchestratorSettings.from_system_config()
        try:
            if not bool(settings.sgw.enabled):
                store = SgwCacheStore()
                manager = SgwManager(settings=settings, store=store, service_groups=[])
                set_sgw_startup_success([], store, manager, self._now_epoch())
                self.logger.info("SGW startup skipped (sgw.enabled is false).")
                return

            state_dir_value = str(settings.state_dir).strip() if settings.state_dir is not None else ""
            if state_dir_value == "":
                message = "state_dir must be set for SGW discovery"
                set_sgw_startup_failure(message)
                self.logger.error("SG discovery failed: %s", message)
                return

            hostname = str(settings.adapter.hostname).strip()
            if hostname == "":
                message = "adapter.hostname must be set for SG discovery"
                set_sgw_startup_failure(message)
                self.logger.error("SG discovery failed: %s", message)
                return

            try:
                service = CmtsInventoryDiscoveryService(
                    cmts_hostname=settings.adapter.hostname,
                    read_community=settings.adapter.community,
                    write_community=settings.adapter.write_community,
                    port=int(settings.adapter.port),
                )
                result = await service.discover_inventory(state_dir=Path(state_dir_value))
                discovered_sg_ids = sorted(result.discovered_sg_ids, key=int)
            except Exception as exc:
                message = str(exc)
                set_sgw_startup_failure(message)
                self.logger.error("SG discovery failed: %s", message)
                return

            store = SgwCacheStore()
            manager = SgwManager(
                settings=settings,
                store=store,
                service_groups=discovered_sg_ids,
                heavy_poller=sgw_heavy_poller,
                light_poller=sgw_light_poller,
            )
            now_epoch = self._now_epoch()
            try:
                await asyncio.to_thread(manager.refresh_once, now_epoch)
            except Exception as exc:
                message = str(exc)
                set_sgw_startup_prime_failure(discovered_sg_ids, message)
                self.logger.exception("SGW priming failed: %s", message)
                return
            set_sgw_startup_success(discovered_sg_ids, store, manager, now_epoch)
            if not self._pytest_running():
                start_sgw_background_refresh()

            ready, _missing = compute_sgw_cache_ready(discovered_sg_ids, store)
            self.logger.info("Discovered SG IDs: %s", [int(sg_id) for sg_id in discovered_sg_ids])
            self.logger.info("SGW initialized for %d service groups.", len(discovered_sg_ids))
            self.logger.info("SGW readiness after prime: %s", "ready" if ready else "not_ready")
        except Exception as exc:
            message = str(exc)
            set_sgw_startup_failure(message)
            self.logger.exception("SGW startup failed: %s", message)

    @staticmethod
    def _now_epoch() -> float:
        return float(time.time())

    @staticmethod
    def _pytest_running() -> bool:
        return os.getenv("PYTEST_CURRENT_TEST") is not None


__all__ = [
    "SgwStartupService",
]

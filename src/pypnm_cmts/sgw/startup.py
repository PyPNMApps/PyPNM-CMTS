# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
import logging
import os
import time

from pypnm_cmts.config.orchestrator_config import (
    DEFAULT_SGW_DISCOVERY_MODE,
    CmtsOrchestratorSettings,
)
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.discovery import (
    ServiceGroupDiscovery,
    SnmpServiceGroupDiscovery,
    StaticServiceGroupDiscovery,
)
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.pollers.heavy import sgw_heavy_poller
from pypnm_cmts.sgw.pollers.light import sgw_light_poller
from pypnm_cmts.sgw.precheck import CmtsStartupPrecheck
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

    def __init__(self, discovery: ServiceGroupDiscovery | None = None) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._discovery = discovery

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

            mode_value = str(settings.sgw.discovery.mode).strip().lower()
            if mode_value == "":
                mode_value = DEFAULT_SGW_DISCOVERY_MODE
            self.logger.info("SGW discovery mode: %s", mode_value)

            if self._precheck_required(settings):
                precheck = CmtsStartupPrecheck()
                precheck_result = await precheck.run(settings)
                self.logger.info(
                    "CMTS precheck: hostname=%s inet=%s ping=%s snmp=%s",
                    str(precheck_result.hostname),
                    str(precheck_result.inet),
                    "ok" if precheck_result.ping_ok else "failed",
                    "ok" if precheck_result.snmp_ok else "failed",
                )
                if not precheck_result.is_ok():
                    message = precheck_result.error_message if precheck_result.error_message != "" else "cmts precheck failed"
                    set_sgw_startup_failure(message)
                    self.logger.error("SG discovery failed: %s", message)
                    return

            try:
                discovery = self._resolve_discovery(settings)
                discovered_sg_ids = await asyncio.to_thread(discovery.discover, settings)
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
            self.logger.info("SGWorkerID: %s", [self._format_worker_id(sg_id) for sg_id in discovered_sg_ids])
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

    def _resolve_discovery(self, settings: CmtsOrchestratorSettings) -> ServiceGroupDiscovery:
        if self._discovery is not None:
            return self._discovery
        mode_value = str(settings.sgw.discovery.mode).strip().lower()
        if mode_value == "":
            mode_value = DEFAULT_SGW_DISCOVERY_MODE
        if mode_value == "snmp":
            return SnmpServiceGroupDiscovery()
        return StaticServiceGroupDiscovery()

    @staticmethod
    def _precheck_required(settings: CmtsOrchestratorSettings) -> bool:
        mode_value = str(settings.sgw.discovery.mode).strip().lower()
        if mode_value == "":
            mode_value = DEFAULT_SGW_DISCOVERY_MODE
        return mode_value == "snmp"

    @staticmethod
    def _format_worker_id(sg_id: ServiceGroupId) -> str:
        return f"sgw-{int(sg_id)}"


__all__ = [
    "SgwStartupService",
]

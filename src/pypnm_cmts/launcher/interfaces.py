from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from abc import ABC, abstractmethod

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings


class WorkerLauncher(ABC):
    """Abstract worker launcher interface for SG execution boundaries."""

    @abstractmethod
    def start_worker(self, sg_id: str, settings: CmtsOrchestratorSettings) -> None:
        """Start a worker for the given service group."""

    @abstractmethod
    def stop_worker(self, sg_id: str) -> None:
        """Stop the worker for the given service group."""

    @abstractmethod
    def list_workers(self) -> list[str]:
        """Return a list of active worker identifiers."""

    @abstractmethod
    def get_worker_status(self, sg_id: str) -> str:
        """Return a status string for the specified worker."""

from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
from abc import ABC, abstractmethod


class LeaderElection(ABC):
    """Abstract leader election interface for controller coordination."""

    @abstractmethod
    def acquire(self) -> bool:
        """Attempt to acquire leadership."""

    @abstractmethod
    def release(self) -> None:
        """Release leadership."""

    @abstractmethod
    def is_leader(self) -> bool:
        """Return True if this instance is the leader."""


class ServiceGroupLease(ABC):
    """Abstract service group lease interface for worker coordination."""

    @abstractmethod
    def acquire_lease(self, sg_id: str) -> bool:
        """Attempt to acquire the lease for a service group."""

    @abstractmethod
    def renew_lease(self, sg_id: str) -> bool:
        """Renew the lease for a service group."""

    @abstractmethod
    def release_lease(self, sg_id: str) -> None:
        """Release the lease for a service group."""

    @abstractmethod
    def get_owner(self, sg_id: str) -> str:
        """Return the owner identifier for the service group lease."""

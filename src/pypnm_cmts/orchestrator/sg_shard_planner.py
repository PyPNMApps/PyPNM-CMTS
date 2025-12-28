# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.config.orchestrator_config import ServiceGroupDescriptor
from pypnm_cmts.lib.types import ServiceGroupId


class ServiceGroupShardPlanner:
    """
    Deterministic planner for ordering enabled service groups and sizing workers.
    """

    MIN_TARGET_SERVICE_GROUPS = 0
    MIN_WORKER_CAP = 0
    MIN_DIVISOR = 1
    SHARD_MODE_SEQUENTIAL = "sequential"
    SHARD_MODE_SCORE = "score"

    @staticmethod
    def plan(
        descriptors: list[ServiceGroupDescriptor],
        shard_mode: str,
        target_service_groups: int,
        worker_cap: int,
    ) -> tuple[list[ServiceGroupId], int]:
        """
        Plan deterministic service group ordering and worker count.

        Args:
            descriptors (list[ServiceGroupDescriptor]): Service group descriptors to plan from.
            shard_mode (str): Sharding mode (sequential or score placeholder).
            target_service_groups (int): Target service groups per worker (0 means all).
            worker_cap (int): Optional cap on worker count (0 means no cap).

        Returns:
            tuple[list[ServiceGroupId], int]: Planned service group ids and worker count.
        """
        enabled = [entry for entry in descriptors if bool(entry.enabled)]
        enabled_sg_ids = [entry.sg_id for entry in enabled]
        ordered = ServiceGroupShardPlanner._order_sg_ids(enabled_sg_ids, shard_mode)
        worker_count = ServiceGroupShardPlanner._compute_worker_count(
            sg_count=len(ordered),
            target_service_groups=int(target_service_groups),
            worker_cap=int(worker_cap),
        )
        return (ordered, worker_count)

    @staticmethod
    def _order_sg_ids(sg_ids: list[ServiceGroupId], shard_mode: str) -> list[ServiceGroupId]:
        match shard_mode:
            case ServiceGroupShardPlanner.SHARD_MODE_SCORE:
                return ServiceGroupShardPlanner._order_by_score(sg_ids)
            case ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL:
                return ServiceGroupShardPlanner._order_sequential(sg_ids)
            case _:
                return ServiceGroupShardPlanner._order_sequential(sg_ids)

    @staticmethod
    def _order_sequential(sg_ids: list[ServiceGroupId]) -> list[ServiceGroupId]:
        return sorted(sg_ids, key=int)

    @staticmethod
    def _order_by_score(sg_ids: list[ServiceGroupId]) -> list[ServiceGroupId]:
        """
        Placeholder: score mode currently returns sequential ordering.
        """
        return sorted(sg_ids, key=int)

    @staticmethod
    def _compute_worker_count(sg_count: int, target_service_groups: int, worker_cap: int) -> int:
        sg_count_value = int(sg_count)
        if sg_count_value <= 0:
            return 0

        target_value = int(target_service_groups)
        if target_value <= ServiceGroupShardPlanner.MIN_TARGET_SERVICE_GROUPS:
            worker_count = sg_count_value
        else:
            divisor = max(ServiceGroupShardPlanner.MIN_DIVISOR, target_value)
            worker_count = int((sg_count_value + divisor - 1) // divisor)

        if worker_count < ServiceGroupShardPlanner.MIN_DIVISOR:
            worker_count = ServiceGroupShardPlanner.MIN_DIVISOR

        cap_value = int(worker_cap)
        if cap_value > ServiceGroupShardPlanner.MIN_WORKER_CAP:
            worker_count = min(worker_count, cap_value)

        return worker_count


__all__ = [
    "ServiceGroupShardPlanner",
]

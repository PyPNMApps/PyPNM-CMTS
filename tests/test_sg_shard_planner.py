# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.config.orchestrator_config import ServiceGroupDescriptor
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.sg_shard_planner import ServiceGroupShardPlanner


def test_shard_planner_sequential_orders_enabled() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(3), enabled=False),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL,
        target_service_groups=2,
        worker_cap=0,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2]
    assert worker_count == 1


def test_shard_planner_score_mode_matches_sequential() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(3), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SCORE,
        target_service_groups=1,
        worker_cap=0,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2, 3]
    assert worker_count == 3


def test_shard_planner_target_zero_means_all() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(3), enabled=True),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL,
        target_service_groups=0,
        worker_cap=0,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2, 3]
    assert worker_count == 3


def test_shard_planner_worker_count_target_one() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL,
        target_service_groups=1,
        worker_cap=0,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2]
    assert worker_count == 2


def test_shard_planner_worker_count_target_two_odd() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(3), enabled=True),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL,
        target_service_groups=2,
        worker_cap=0,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2, 3]
    assert worker_count == 2


def test_shard_planner_worker_count_target_two_even() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(3), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(4), enabled=True),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL,
        target_service_groups=2,
        worker_cap=0,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2, 3, 4]
    assert worker_count == 2


def test_shard_planner_worker_count_empty() -> None:
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=[],
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SEQUENTIAL,
        target_service_groups=2,
        worker_cap=0,
    )
    assert planned == []
    assert worker_count == 0


def test_shard_planner_worker_count_with_cap() -> None:
    descriptors = [
        ServiceGroupDescriptor(sg_id=ServiceGroupId(1), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(2), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(3), enabled=True),
        ServiceGroupDescriptor(sg_id=ServiceGroupId(4), enabled=True),
    ]
    planned, worker_count = ServiceGroupShardPlanner.plan(
        descriptors=descriptors,
        shard_mode=ServiceGroupShardPlanner.SHARD_MODE_SCORE,
        target_service_groups=2,
        worker_cap=1,
    )
    assert [int(sg_id) for sg_id in planned] == [1, 2, 3, 4]
    assert worker_count == 1

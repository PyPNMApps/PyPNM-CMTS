# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    LeaderId,
    OwnerId,
    ServiceGroupId,
)

ELECTION_NAME = CoordinationElectionName("coordination-test")
LEADER_A = LeaderId("leader-a")
LEADER_B = LeaderId("leader-b")
OWNER_A = OwnerId("owner-a")
OWNER_B = OwnerId("owner-b")
SG_1 = ServiceGroupId(1)
SG_2 = ServiceGroupId(2)
LEADER_TTL = 5
LEASE_TTL = 10


def test_not_leader_can_acquire_leases(tmp_path: Path) -> None:
    clock = [100.0]

    def now() -> float:
        return clock[0]

    leader = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )
    follower = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        owner_id=OWNER_B,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )

    leader.tick([SG_1, SG_2])
    follower.tick([SG_1, SG_2])
    status_a = leader.status()
    status_b = follower.status()

    assert status_a.is_leader is True
    assert status_b.is_leader is False
    assert len(status_a.held_sg_ids) == 1
    assert len(status_b.held_sg_ids) == 1
    assert set(status_a.held_sg_ids).intersection(set(status_b.held_sg_ids)) == set()


def test_leader_acquires_leases(tmp_path: Path) -> None:
    clock = [200.0]

    def now() -> float:
        return clock[0]

    manager = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=2,
        now=now,
    )

    result = manager.tick([SG_1, SG_2])

    assert result.is_leader is True
    assert set(result.acquired_sg_ids) == {SG_1, SG_2}


def test_leader_renew_extends_ttl(tmp_path: Path) -> None:
    clock = [300.0]

    def now() -> float:
        return clock[0]

    manager = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )

    first = manager.tick([SG_1])
    clock[0] = 304.0
    second = manager.tick([SG_1])

    assert first.is_leader is True
    assert second.is_leader is True
    assert second.renewed_sg_ids == [SG_1]


def test_failover_allows_other_leader(tmp_path: Path) -> None:
    clock = [400.0]

    def now() -> float:
        return clock[0]

    manager_a = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )
    manager_b = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        owner_id=OWNER_B,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )

    manager_a.tick([SG_1])
    clock[0] = 411.0

    result_b = manager_b.tick([SG_1])

    assert result_b.is_leader is True
    assert result_b.acquired_sg_ids == [SG_1]


def test_release_all_clears_leader_and_leases(tmp_path: Path) -> None:
    clock = [500.0]

    def now() -> float:
        return clock[0]

    manager = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=2,
        now=now,
    )

    manager.tick([SG_1, SG_2])
    release_result = manager.release_all()

    assert release_result.released_leader is True
    assert set(release_result.released_sg_ids) == {SG_1, SG_2}


def test_managers_converge_to_disjoint_leases(tmp_path: Path) -> None:
    clock = [600.0]

    def now() -> float:
        return clock[0]

    manager_a = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=2,
        now=now,
    )
    manager_b = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        owner_id=OWNER_B,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=2,
        now=now,
    )

    service_groups = [SG_1, SG_2, ServiceGroupId(3), ServiceGroupId(4)]

    for _ in range(6):
        manager_a.tick(service_groups)
        manager_b.tick(service_groups)

        held_a = set(manager_a.status().held_sg_ids)
        held_b = set(manager_b.status().held_sg_ids)
        if len(held_a) == 2 and len(held_b) == 2 and held_a.intersection(held_b) == set():
            break

    held_a = set(manager_a.status().held_sg_ids)
    held_b = set(manager_b.status().held_sg_ids)

    assert len(held_a) == 2
    assert len(held_b) == 2
    assert held_a.intersection(held_b) == set()


def test_score_shard_converges_to_disjoint_leases(tmp_path: Path) -> None:
    clock = [650.0]

    def now() -> float:
        return clock[0]

    manager_a = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=2,
        shard_mode=CoordinationManager.SHARD_MODE_SCORE,
        now=now,
    )
    manager_b = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        owner_id=OWNER_B,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=2,
        shard_mode=CoordinationManager.SHARD_MODE_SCORE,
        now=now,
    )

    service_groups = [
        SG_1,
        SG_2,
        ServiceGroupId(3),
        ServiceGroupId(4),
        ServiceGroupId(5),
        ServiceGroupId(6),
    ]

    for _ in range(8):
        manager_a.tick(service_groups)
        manager_b.tick(service_groups)

        held_a = set(manager_a.status().held_sg_ids)
        held_b = set(manager_b.status().held_sg_ids)
        if len(held_a) == 2 and len(held_b) == 2 and held_a.intersection(held_b) == set():
            break

    held_a = set(manager_a.status().held_sg_ids)
    held_b = set(manager_b.status().held_sg_ids)

    assert len(held_a) == 2
    assert len(held_b) == 2
    assert held_a.intersection(held_b) == set()


def test_leader_uniqueness_and_renewal(tmp_path: Path) -> None:
    clock = [700.0]

    def now() -> float:
        return clock[0]

    manager_a = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        owner_id=OWNER_A,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )
    manager_b = CoordinationManager(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        owner_id=OWNER_B,
        leader_ttl_seconds=LEADER_TTL,
        lease_ttl_seconds=LEASE_TTL,
        target_service_groups=1,
        now=now,
    )

    manager_a.tick([SG_1])
    manager_b.tick([SG_1])

    status_a = manager_a.status()
    status_b = manager_b.status()
    assert (status_a.is_leader and status_b.is_leader) is False

    leader_manager = manager_a if status_a.is_leader else manager_b
    before = leader_manager.leader_status().expires_at

    clock[0] = 702.0
    leader_manager.tick([SG_1])
    after = leader_manager.leader_status().expires_at

    assert after > before

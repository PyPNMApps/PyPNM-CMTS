# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os
from pathlib import Path

from pypnm_cmts.coordination.service_group_lease import FileServiceGroupLease
from pypnm_cmts.lib.types import CoordinationElectionName, OwnerId, ServiceGroupId

ELECTION_NAME = CoordinationElectionName("test-election")
SG_ID = ServiceGroupId(7)
TTL_SECONDS = 10
OWNER_A = OwnerId("owner-a")
OWNER_B = OwnerId("owner-b")
LOCK_SUFFIX = ".lock"


def test_invalid_ttl_raises(tmp_path: Path) -> None:
    raised = False
    try:
        FileServiceGroupLease(
            state_dir=tmp_path,
            election_name=ELECTION_NAME,
            sg_id=SG_ID,
            owner_id=OWNER_A,
            ttl_seconds=0,
        )
    except ValueError:
        raised = True
    assert raised is True


def test_lease_first_acquire(tmp_path: Path) -> None:
    clock = [100.0]

    def now() -> float:
        return clock[0]

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.try_acquire()

    assert result.acquired is True
    assert result.is_owner is True
    assert result.owner_id == OWNER_A


def test_second_contender_fails_when_ttl_valid(tmp_path: Path) -> None:
    clock = [200.0]

    def now() -> float:
        return clock[0]

    lease_a = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )
    lease_b = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_B,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    assert lease_a.try_acquire().acquired is True
    result_b = lease_b.try_acquire()

    assert result_b.acquired is False
    assert result_b.owner_id == OWNER_A


def test_try_acquire_busy_lock_returns_false(tmp_path: Path) -> None:
    clock = [250.0]

    def now() -> float:
        return clock[0]

    lock_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}{LOCK_SUFFIX}"
    lock_path.mkdir()

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.try_acquire()

    assert result.acquired is False
    assert result.is_owner is False


def test_renew_busy_lock_returns_false(tmp_path: Path) -> None:
    clock = [275.0]

    def now() -> float:
        return clock[0]

    lock_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}{LOCK_SUFFIX}"
    lock_path.mkdir()

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.renew()

    assert result.renewed is False
    assert result.is_owner is False


def test_release_busy_lock_returns_false(tmp_path: Path) -> None:
    clock = [285.0]

    def now() -> float:
        return clock[0]

    lock_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}{LOCK_SUFFIX}"
    lock_path.mkdir()

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.release()

    assert result.released is False
    assert result.is_owner is False


def test_after_ttl_expiry_another_contender_acquires(tmp_path: Path) -> None:
    clock = [300.0]

    def now() -> float:
        return clock[0]

    lease_a = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )
    lease_b = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_B,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    assert lease_a.try_acquire().acquired is True
    clock[0] = 312.0

    result_b = lease_b.try_acquire()

    assert result_b.acquired is True
    assert result_b.owner_id == OWNER_B


def test_renew_extends_ttl_only_for_owner(tmp_path: Path) -> None:
    clock = [400.0]

    def now() -> float:
        return clock[0]

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    acquired = lease.try_acquire()
    clock[0] = 405.0
    renewed = lease.renew()

    assert acquired.acquired is True
    assert renewed.renewed is True
    assert renewed.expires_at > acquired.expires_at


def test_release_clears_lease(tmp_path: Path) -> None:
    clock = [500.0]

    def now() -> float:
        return clock[0]

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    assert lease.try_acquire().acquired is True
    released = lease.release()

    assert released.released is True
    assert lease.status().is_owner is False


def test_corrupted_record_allows_acquire(tmp_path: Path) -> None:
    clock = [600.0]

    def now() -> float:
        return clock[0]

    state_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}.json"
    state_path.write_text("not-json", encoding="utf-8")

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.try_acquire()

    assert result.acquired is True
    assert result.owner_id == OWNER_A


def test_corrupt_record_numeric_fields_does_not_crash(tmp_path: Path) -> None:
    clock = [650.0]

    def now() -> float:
        return clock[0]

    state_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}.json"
    state_path.write_text(
        '{"election_name":"test-election","sg_id":7,"owner_id":"owner-a","acquired_at":"bad","expires_at":"bad"}',
        encoding="utf-8",
    )

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_B,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.try_acquire()

    assert result.acquired is True
    assert result.owner_id == OWNER_B


def test_election_name_mismatch_ignored(tmp_path: Path) -> None:
    clock = [700.0]

    def now() -> float:
        return clock[0]

    state_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}.json"
    state_path.write_text(
        '{"election_name":"other-election","sg_id":7,"owner_id":"owner-a","acquired_at":700,"expires_at":710}',
        encoding="utf-8",
    )

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_B,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.try_acquire()

    assert result.acquired is True
    assert result.owner_id == OWNER_B


def test_stale_lock_is_broken_and_acquire_succeeds(tmp_path: Path) -> None:
    clock = [800.0]

    def now() -> float:
        return clock[0]

    lock_path = tmp_path / f"{ELECTION_NAME}.sg-{SG_ID}{LOCK_SUFFIX}"
    lock_path.mkdir()
    stale_time = clock[0] - 100.0
    lock_path.touch()
    lock_path.chmod(0o700)
    lock_path.stat()
    lock_path_utime = (stale_time, stale_time)
    os.utime(lock_path, lock_path_utime)

    lease = FileServiceGroupLease(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        sg_id=SG_ID,
        owner_id=OWNER_A,
        ttl_seconds=TTL_SECONDS,
        now=now,
    )

    result = lease.try_acquire()

    assert result.acquired is True
    assert result.owner_id == OWNER_A

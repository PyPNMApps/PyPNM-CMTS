# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os
from pathlib import Path

from pypnm_cmts.coordination.leader_election import FileLeaderElection
from pypnm_cmts.lib.types import CoordinationElectionName, LeaderId

ELECTION_NAME = CoordinationElectionName("test-election")
LEADER_A = LeaderId("leader-a")
LEADER_B = LeaderId("leader-b")


def test_invalid_ttl_raises(tmp_path: Path) -> None:
    raised = False
    try:
        FileLeaderElection(
            state_dir=tmp_path,
            election_name=ELECTION_NAME,
            leader_id=LEADER_A,
            ttl_seconds=0,
        )
    except ValueError:
        raised = True
    assert raised is True


def test_leader_first_acquire(tmp_path: Path) -> None:
    clock = [100.0]

    def now() -> float:
        return clock[0]

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )

    result = election.try_acquire()

    assert result.acquired is True
    assert result.is_leader is True
    assert result.leader_id == LEADER_A


def test_second_contender_fails_when_ttl_valid(tmp_path: Path) -> None:
    clock = [200.0]

    def now() -> float:
        return clock[0]

    leader_a = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )
    leader_b = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        ttl_seconds=10,
        now=now,
    )

    assert leader_a.try_acquire().acquired is True
    result_b = leader_b.try_acquire()

    assert result_b.acquired is False
    assert result_b.is_leader is False
    assert result_b.leader_id == LEADER_A


def test_try_acquire_busy_lock_returns_false(tmp_path: Path) -> None:
    clock = [250.0]

    def now() -> float:
        return clock[0]

    lock_path = tmp_path / f"{ELECTION_NAME}.lock"
    lock_path.mkdir()

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )

    result = election.try_acquire()

    assert result.acquired is False
    assert result.is_leader is False


def test_after_ttl_expiry_another_contender_acquires(tmp_path: Path) -> None:
    clock = [300.0]

    def now() -> float:
        return clock[0]

    leader_a = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=5,
        now=now,
    )
    leader_b = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        ttl_seconds=5,
        now=now,
    )

    assert leader_a.try_acquire().acquired is True
    clock[0] = 306.0

    result_b = leader_b.try_acquire()

    assert result_b.acquired is True
    assert result_b.leader_id == LEADER_B


def test_renew_extends_ttl(tmp_path: Path) -> None:
    clock = [400.0]

    def now() -> float:
        return clock[0]

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )

    acquired = election.try_acquire()
    clock[0] = 405.0
    renewed = election.renew()

    assert acquired.acquired is True
    assert renewed.renewed is True
    assert renewed.expires_at > acquired.expires_at


def test_release_clears_leadership(tmp_path: Path) -> None:
    clock = [500.0]

    def now() -> float:
        return clock[0]

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )

    assert election.try_acquire().acquired is True
    released = election.release()

    assert released.released is True
    assert election.status().is_leader is False


def test_corrupted_record_allows_acquire(tmp_path: Path) -> None:
    clock = [600.0]

    def now() -> float:
        return clock[0]

    state_path = tmp_path / f"{ELECTION_NAME}.json"
    state_path.write_text("not-json", encoding="utf-8")

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )

    result = election.try_acquire()

    assert result.acquired is True
    assert result.leader_id == LEADER_A


def test_corrupt_record_numeric_fields_does_not_crash(tmp_path: Path) -> None:
    clock = [650.0]

    def now() -> float:
        return clock[0]

    state_path = tmp_path / f"{ELECTION_NAME}.json"
    state_path.write_text(
        f'{{"election_name":"{ELECTION_NAME}","leader_id":"{LEADER_A}","acquired_at":"bad","expires_at":"bad"}}',
        encoding="utf-8",
    )

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        ttl_seconds=10,
        now=now,
    )

    result = election.try_acquire()

    assert result.acquired is True
    assert result.leader_id == LEADER_B


def test_election_name_mismatch_ignored(tmp_path: Path) -> None:
    clock = [700.0]

    def now() -> float:
        return clock[0]

    state_path = tmp_path / f"{ELECTION_NAME}.json"
    state_path.write_text(
        '{"election_name":"other-election","leader_id":"leader-a","acquired_at":700,"expires_at":710}',
        encoding="utf-8",
    )

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_B,
        ttl_seconds=10,
        now=now,
    )

    result = election.try_acquire()

    assert result.acquired is True
    assert result.leader_id == LEADER_B


def test_stale_lock_is_broken_and_acquire_succeeds(tmp_path: Path) -> None:
    clock = [800.0]

    def now() -> float:
        return clock[0]

    lock_path = tmp_path / f"{ELECTION_NAME}.lock"
    lock_path.mkdir()
    stale_time = clock[0] - 100.0
    lock_path.touch()
    lock_path.chmod(0o700)
    lock_path.stat()
    lock_path_utime = (stale_time, stale_time)
    os.utime(lock_path, lock_path_utime)

    election = FileLeaderElection(
        state_dir=tmp_path,
        election_name=ELECTION_NAME,
        leader_id=LEADER_A,
        ttl_seconds=10,
        now=now,
    )

    result = election.try_acquire()

    assert result.acquired is True
    assert result.leader_id == LEADER_A

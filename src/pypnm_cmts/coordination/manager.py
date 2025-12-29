# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from pypnm_cmts.coordination.leader_election import FileLeaderElection
from pypnm_cmts.coordination.models import (
    CoordinationReleaseAllResultModel,
    CoordinationStatusModel,
    CoordinationTickResultModel,
    LeaderElectionStatusModel,
)
from pypnm_cmts.coordination.service_group_lease import FileServiceGroupLease
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    LeaderId,
    OwnerId,
    ServiceGroupId,
)


class CoordinationManager:
    """
    Coordination manager that wires leader election and service group leases.
    """

    MESSAGE_NOT_LEADER = "Leader not held; lease operations complete."
    MESSAGE_LEADER_ACTIVE = "Leader active; lease operations complete."
    MESSAGE_RELEASED = "Leader and leases released."
    MIN_TARGET_SERVICE_GROUPS = 0
    SHARD_MODE_SEQUENTIAL = "sequential"
    SHARD_MODE_SCORE = "score"
    SHARD_MODE_DEFAULT = SHARD_MODE_SEQUENTIAL
    SCORE_DIGEST_BYTES = 8

    def __init__(
        self,
        state_dir: Path,
        election_name: CoordinationElectionName,
        leader_id: LeaderId,
        owner_id: OwnerId,
        leader_ttl_seconds: int,
        lease_ttl_seconds: int,
        target_service_groups: int,
        shard_mode: str = SHARD_MODE_DEFAULT,
        leader_enabled: bool = True,
        leader_id_validator: Callable[[LeaderId], bool] | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        """
        Initialize coordination manager with leader election and lease settings.

        Args:
            state_dir (Path): Base directory for coordination state files.
            election_name (CoordinationElectionName): Logical election namespace.
            leader_id (LeaderId): Identifier for leader election ownership.
            owner_id (OwnerId): Identifier for service group lease ownership.
            leader_ttl_seconds (int): TTL in seconds for leader election.
            lease_ttl_seconds (int): TTL in seconds for service group leases.
            target_service_groups (int): Target number of service groups to hold.
            shard_mode (str): Sharding mode for candidate ordering.
            leader_enabled (bool): When false, skip leader election writes.
            leader_id_validator (Callable[[LeaderId], bool] | None): Optional validator for leader records.
            now (Callable[[], float] | None): Optional time provider for testing.
        """
        if int(target_service_groups) < self.MIN_TARGET_SERVICE_GROUPS:
            raise ValueError("target_service_groups must be non-negative.")
        if shard_mode not in (self.SHARD_MODE_SEQUENTIAL, self.SHARD_MODE_SCORE):
            raise ValueError("shard_mode must be 'sequential' or 'score'.")
        self._state_dir = state_dir
        self._election_name = election_name
        self._leader_id = leader_id
        self._owner_id = owner_id
        self._leader_ttl_seconds = int(leader_ttl_seconds)
        self._lease_ttl_seconds = int(lease_ttl_seconds)
        self._target_service_groups = int(target_service_groups)
        self._shard_mode = shard_mode
        self._leader_enabled = leader_enabled
        self._now = now
        self._held_leases: set[ServiceGroupId] = set()

        self._leader_election = FileLeaderElection(
            state_dir=self._state_dir,
            election_name=self._election_name,
            leader_id=self._leader_id,
            ttl_seconds=self._leader_ttl_seconds,
            leader_id_validator=leader_id_validator,
            now=self._now,
        )

    def tick(self, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        """
        Execute one deterministic coordination step.

        Leader election is acquired or renewed each tick. Service group lease
        operations occur regardless of leader state. The manager maintains up to
        target_service_groups leases using deterministic renew, release, and
        acquire ordering.

        Args:
            service_groups (list[ServiceGroupId]): Service groups to coordinate.

        Returns:
            CoordinationTickResultModel: Summary of leader state and lease actions.
        """
        acquired_sg_ids: list[ServiceGroupId] = []
        renewed_sg_ids: list[ServiceGroupId] = []
        released_sg_ids: list[ServiceGroupId] = []
        failed_sg_ids: list[ServiceGroupId] = []

        if self._leader_enabled:
            leader_result = self._leader_election.try_acquire()
            if leader_result.is_leader and not leader_result.acquired:
                renew_result = self._leader_election.renew()
                if renew_result.renewed:
                    leader_result = renew_result
        else:
            leader_status = self._leader_election.status()
            leader_result = LeaderElectionStatusModel(
                election_name=leader_status.election_name,
                is_leader=leader_status.is_leader,
                leader_id=leader_status.leader_id,
                acquired_at=leader_status.acquired_at,
                expires_at=leader_status.expires_at,
                remaining_seconds=leader_status.remaining_seconds,
                state_path=leader_status.state_path,
                message=leader_status.message,
            )

        held_sorted = self._sorted_held_leases()
        for sg_id in held_sorted:
            lease = self._lease_for_sg(sg_id)
            renew_result = lease.renew()
            if renew_result.renewed:
                renewed_sg_ids.append(sg_id)
            else:
                self._held_leases.discard(sg_id)
                failed_sg_ids.append(sg_id)

        target_count = self._target_service_groups
        if len(self._held_leases) > target_count:
            for sg_id in self._sorted_held_leases(reverse=True):
                if len(self._held_leases) <= target_count:
                    break
                lease = self._lease_for_sg(sg_id)
                release_result = lease.release()
                if release_result.released:
                    self._held_leases.discard(sg_id)
                    released_sg_ids.append(sg_id)
                else:
                    failed_sg_ids.append(sg_id)

        if len(self._held_leases) < target_count:
            attempted: set[ServiceGroupId] = set()
            for sg_id in self._candidate_service_groups(service_groups):
                if len(self._held_leases) >= target_count:
                    break
                if sg_id in self._held_leases:
                    continue
                attempted.add(sg_id)
                lease = self._lease_for_sg(sg_id)
                acquire_result = lease.try_acquire()
                if acquire_result.acquired:
                    self._held_leases.add(sg_id)
                    acquired_sg_ids.append(sg_id)
                else:
                    failed_sg_ids.append(sg_id)

            if len(self._held_leases) < target_count:
                for sg_id in self._sorted_service_groups(service_groups):
                    if len(self._held_leases) >= target_count:
                        break
                    if sg_id in self._held_leases:
                        continue
                    if sg_id in attempted:
                        continue
                    lease = self._lease_for_sg(sg_id)
                    acquire_result = lease.try_acquire()
                    if acquire_result.acquired:
                        self._held_leases.add(sg_id)
                        acquired_sg_ids.append(sg_id)
                    else:
                        failed_sg_ids.append(sg_id)

        return CoordinationTickResultModel(
            is_leader=leader_result.is_leader,
            leader_id=leader_result.leader_id,
            acquired_sg_ids=acquired_sg_ids,
            renewed_sg_ids=renewed_sg_ids,
            released_sg_ids=released_sg_ids,
            failed_sg_ids=failed_sg_ids,
            message=self.MESSAGE_LEADER_ACTIVE if leader_result.is_leader else self.MESSAGE_NOT_LEADER,
        )

    def tick_leader_only(self) -> CoordinationTickResultModel:
        """
        Execute a leader-only coordination step without service group leases.

        Returns:
            CoordinationTickResultModel: Summary of leader election state with empty lease actions.
        """
        if self._leader_enabled:
            leader_result = self._leader_election.try_acquire()
            if leader_result.is_leader and not leader_result.acquired:
                renew_result = self._leader_election.renew()
                if renew_result.renewed:
                    leader_result = renew_result
        else:
            leader_status = self._leader_election.status()
            leader_result = LeaderElectionStatusModel(
                election_name=leader_status.election_name,
                is_leader=leader_status.is_leader,
                leader_id=leader_status.leader_id,
                acquired_at=leader_status.acquired_at,
                expires_at=leader_status.expires_at,
                remaining_seconds=leader_status.remaining_seconds,
                state_path=leader_status.state_path,
                message=leader_status.message,
            )

        return CoordinationTickResultModel(
            is_leader=leader_result.is_leader,
            leader_id=leader_result.leader_id,
            acquired_sg_ids=[],
            renewed_sg_ids=[],
            released_sg_ids=[],
            failed_sg_ids=[],
            message=self.MESSAGE_LEADER_ACTIVE if leader_result.is_leader else self.MESSAGE_NOT_LEADER,
        )

    def release_all(self) -> CoordinationReleaseAllResultModel:
        """
        Release all leases held by this manager and relinquish leadership.

        Returns:
            CoordinationReleaseAllResultModel: Summary of released resources.
        """
        released_sg_ids: list[ServiceGroupId] = []
        failed_sg_ids: list[ServiceGroupId] = []

        for sg_id in list(self._held_leases):
            lease = self._lease_for_sg(sg_id)
            release_result = lease.release()
            if release_result.released:
                released_sg_ids.append(sg_id)
                self._held_leases.discard(sg_id)
            else:
                failed_sg_ids.append(sg_id)

        leader_release = None
        if self._leader_enabled:
            leader_release = self._leader_election.release()

        return CoordinationReleaseAllResultModel(
            released_leader=leader_release.released if leader_release is not None else False,
            released_sg_ids=released_sg_ids,
            failed_sg_ids=failed_sg_ids,
            message=self.MESSAGE_RELEASED,
        )

    def status(self) -> CoordinationStatusModel:
        """
        Return a summary of current leader and lease state.

        Returns:
            CoordinationStatusModel: Snapshot of leader ownership and held leases.
        """
        leader_status = self._leader_election.status()
        return CoordinationStatusModel(
            is_leader=leader_status.is_leader,
            leader_id=leader_status.leader_id,
            held_sg_ids=sorted(self._held_leases),
            message=leader_status.message,
        )

    def leader_status(self) -> LeaderElectionStatusModel:
        """
        Return the current leader election status.

        Returns:
            LeaderElectionStatusModel: Snapshot of the leader election record.
        """
        return self._leader_election.status()

    def _lease_for_sg(self, sg_id: ServiceGroupId) -> FileServiceGroupLease:
        return FileServiceGroupLease(
            state_dir=self._state_dir,
            election_name=self._election_name,
            sg_id=sg_id,
            owner_id=self._owner_id,
            ttl_seconds=self._lease_ttl_seconds,
            now=self._now,
        )

    def _sorted_held_leases(self, reverse: bool = False) -> list[ServiceGroupId]:
        return sorted(self._held_leases, key=int, reverse=reverse)

    def _candidate_service_groups(self, service_groups: list[ServiceGroupId]) -> list[ServiceGroupId]:
        if self._shard_mode == self.SHARD_MODE_SCORE:
            return self._score_ordered_service_groups(service_groups)
        return self._sorted_service_groups(service_groups)

    def _score_ordered_service_groups(self, service_groups: list[ServiceGroupId]) -> list[ServiceGroupId]:
        scored: list[tuple[int, int, ServiceGroupId]] = []
        for sg_id in service_groups:
            score = self._score_for_sg(sg_id)
            scored.append((-score, int(sg_id), sg_id))
        scored.sort()
        return [item[2] for item in scored]

    def _score_for_sg(self, sg_id: ServiceGroupId) -> int:
        payload = f"{self._owner_id}:{int(sg_id)}".encode()
        digest = hashlib.sha256(payload).digest()
        slice_bytes = digest[: self.SCORE_DIGEST_BYTES]
        return int.from_bytes(slice_bytes, byteorder="big", signed=False)

    @staticmethod
    def _sorted_service_groups(service_groups: list[ServiceGroupId]) -> list[ServiceGroupId]:
        return sorted(service_groups, key=int)

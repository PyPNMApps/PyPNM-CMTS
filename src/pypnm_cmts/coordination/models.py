# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    LeaderId,
    OwnerId,
    ServiceGroupId,
    TickIndex,
)


class LeaderRecordModel(BaseModel):
    election_name: CoordinationElectionName = Field(default=CoordinationElectionName(""), description="Logical election name for the coordination record.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when leadership was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when leadership expires.")


class LeaderElectionStatusModel(BaseModel):
    election_name: CoordinationElectionName = Field(default=CoordinationElectionName(""), description="Logical election name for the coordination record.")
    is_leader: bool = Field(default=False, description="True if the caller is the current leader.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when leadership was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when leadership expires.")
    remaining_seconds: float = Field(default=0.0, description="Seconds remaining until leadership expires.")
    state_path: str = Field(default="", description="Filesystem path for the leader record.")
    message: str = Field(default="", description="Status message.")


class LeaderElectionAcquireResultModel(BaseModel):
    acquired: bool = Field(default=False, description="True if leadership was acquired.")
    is_leader: bool = Field(default=False, description="True if the caller is the leader after the attempt.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when leadership was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when leadership expires.")
    remaining_seconds: float = Field(default=0.0, description="Seconds remaining until leadership expires.")
    message: str = Field(default="", description="Result message.")


class LeaderElectionRenewResultModel(BaseModel):
    renewed: bool = Field(default=False, description="True if leadership TTL was renewed.")
    is_leader: bool = Field(default=False, description="True if the caller is still the leader.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when leadership was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when leadership expires.")
    remaining_seconds: float = Field(default=0.0, description="Seconds remaining until leadership expires.")
    message: str = Field(default="", description="Result message.")


class LeaderElectionReleaseResultModel(BaseModel):
    released: bool = Field(default=False, description="True if leadership was released.")
    is_leader: bool = Field(default=False, description="True if the caller is the leader after release.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    message: str = Field(default="", description="Result message.")


class ServiceGroupLeaseRecordModel(BaseModel):
    election_name: CoordinationElectionName = Field(default=CoordinationElectionName(""), description="Logical election name for the coordination record.")
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the lease.")
    owner_id: OwnerId = Field(default=OwnerId(""), description="Current lease owner identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when lease was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when lease expires.")


class ServiceGroupLeaseStatusModel(BaseModel):
    election_name: CoordinationElectionName = Field(default=CoordinationElectionName(""), description="Logical election name for the coordination record.")
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the lease.")
    is_owner: bool = Field(default=False, description="True if the caller currently owns the lease.")
    owner_id: OwnerId = Field(default=OwnerId(""), description="Current lease owner identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when lease was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when lease expires.")
    remaining_seconds: float = Field(default=0.0, description="Seconds remaining until lease expires.")
    state_path: str = Field(default="", description="Filesystem path for the lease record.")
    message: str = Field(default="", description="Status message.")


class ServiceGroupLeaseAcquireResultModel(BaseModel):
    acquired: bool = Field(default=False, description="True if the lease was acquired.")
    is_owner: bool = Field(default=False, description="True if the caller owns the lease after the attempt.")
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the lease.")
    owner_id: OwnerId = Field(default=OwnerId(""), description="Current lease owner identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when lease was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when lease expires.")
    remaining_seconds: float = Field(default=0.0, description="Seconds remaining until lease expires.")
    message: str = Field(default="", description="Result message.")


class ServiceGroupLeaseRenewResultModel(BaseModel):
    renewed: bool = Field(default=False, description="True if lease TTL was renewed.")
    is_owner: bool = Field(default=False, description="True if the caller owns the lease after renewal.")
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the lease.")
    owner_id: OwnerId = Field(default=OwnerId(""), description="Current lease owner identifier.")
    acquired_at: float = Field(default=0.0, description="Epoch seconds when lease was acquired.")
    expires_at: float = Field(default=0.0, description="Epoch seconds when lease expires.")
    remaining_seconds: float = Field(default=0.0, description="Seconds remaining until lease expires.")
    message: str = Field(default="", description="Result message.")


class ServiceGroupLeaseReleaseResultModel(BaseModel):
    released: bool = Field(default=False, description="True if the lease was released.")
    is_owner: bool = Field(default=False, description="True if the caller owns the lease after release.")
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the lease.")
    owner_id: OwnerId = Field(default=OwnerId(""), description="Current lease owner identifier.")
    message: str = Field(default="", description="Result message.")


class ServiceGroupLeaseConflictModel(BaseModel):
    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the conflict.")
    owner_id: OwnerId = Field(default=OwnerId(""), description="Current lease owner identifier.")
    reason: str = Field(default="", description="Reason the lease could not be acquired.")


class CoordinationTickResultModel(BaseModel):
    tick_index: TickIndex = Field(default=TickIndex(0), description="1-based tick index if provided; 0 when unset.")
    is_leader: bool = Field(default=False, description="True if the caller is the current leader.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    acquired_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups acquired during the tick.")
    renewed_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups renewed during the tick.")
    released_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups released during the tick.")
    failed_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups that failed to acquire, renew, or release.")
    enabled_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Enabled service group identifiers for this tick.")
    desired_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Desired service groups for this tick.")
    leased_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups leased by this coordinator.")
    conflicts: list[ServiceGroupLeaseConflictModel] = Field(default_factory=list, description="Lease conflicts encountered for desired service groups.")
    worker_count: int = Field(default=0, description="Planned worker count derived from shard planning.")
    message: str = Field(default="", description="Summary message for the tick operation.")


class CoordinationStatusModel(BaseModel):
    is_leader: bool = Field(default=False, description="True if the caller is the current leader.")
    leader_id: LeaderId = Field(default=LeaderId(""), description="Current leader identifier.")
    held_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups currently held by this manager.")
    message: str = Field(default="", description="Summary status message.")


class CoordinationReleaseAllResultModel(BaseModel):
    released_leader: bool = Field(default=False, description="True if the leader role was released.")
    released_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups released by this manager.")
    failed_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups that failed to release.")
    message: str = Field(default="", description="Summary message for the release operation.")

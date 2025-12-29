# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import contextlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path

from pypnm_cmts.coordination.models import (
    LeaderElectionAcquireResultModel,
    LeaderElectionReleaseResultModel,
    LeaderElectionRenewResultModel,
    LeaderElectionStatusModel,
    LeaderRecordModel,
)
from pypnm_cmts.lib.types import CoordinationElectionName, LeaderId


class FileLeaderElection:
    """
    File-based leader election using a JSON record with TTL.
    """

    LOCK_SUFFIX = ".lock"
    MIN_TTL_SECONDS = 1
    STALE_LOCK_MULTIPLIER = 2.0

    def __init__(
        self,
        state_dir: Path,
        election_name: CoordinationElectionName,
        leader_id: LeaderId,
        ttl_seconds: int,
        leader_id_validator: Callable[[LeaderId], bool] | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        """
        Initialize a file-based leader election instance.
        """
        if str(election_name).strip() == "":
            raise ValueError("election_name must be non-empty.")
        if str(leader_id).strip() == "":
            raise ValueError("leader_id must be non-empty.")
        if int(ttl_seconds) < self.MIN_TTL_SECONDS:
            raise ValueError("ttl_seconds must be greater than zero.")
        self._state_dir = state_dir
        self._election_name = CoordinationElectionName(str(election_name).strip())
        self._leader_id = LeaderId(str(leader_id).strip())
        self._ttl_seconds = int(ttl_seconds)
        self._leader_id_validator = leader_id_validator
        self._now = now or time.time
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def try_acquire(self) -> LeaderElectionAcquireResultModel:
        """
        Attempt to acquire leadership.
        """
        if not self._acquire_lock():
            return LeaderElectionAcquireResultModel(
                acquired=False,
                is_leader=False,
                leader_id=LeaderId(""),
                acquired_at=0.0,
                expires_at=0.0,
                remaining_seconds=0.0,
                message="Leader election is busy.",
            )

        try:
            record, valid = self._read_record()
            now = self._now()

            new_record = self._new_record(now)
            if valid and not self._is_expired(record, now):
                if record.leader_id == self._leader_id:
                    remaining = self._remaining_seconds(record, now)
                    return LeaderElectionAcquireResultModel(
                        acquired=False,
                        is_leader=True,
                        leader_id=record.leader_id,
                        acquired_at=record.acquired_at,
                        expires_at=record.expires_at,
                        remaining_seconds=remaining,
                        message="Already leader.",
                    )
                remaining = self._remaining_seconds(record, now)
                return LeaderElectionAcquireResultModel(
                    acquired=False,
                    is_leader=False,
                    leader_id=record.leader_id,
                    acquired_at=record.acquired_at,
                    expires_at=record.expires_at,
                    remaining_seconds=remaining,
                    message="Leader already held.",
                )

            if valid:
                self._write_record_replace(new_record)
            else:
                acquired = self._write_record_atomic(new_record)
                if not acquired:
                    self._write_record_replace(new_record)

            remaining = self._remaining_seconds(new_record, now)
            return LeaderElectionAcquireResultModel(
                acquired=True,
                is_leader=True,
                leader_id=new_record.leader_id,
                acquired_at=new_record.acquired_at,
                expires_at=new_record.expires_at,
                remaining_seconds=remaining,
                message="Leadership acquired.",
            )
        finally:
            self._release_lock()

    def renew(self) -> LeaderElectionRenewResultModel:
        """
        Renew leadership TTL if the caller is the current leader.
        """
        if not self._acquire_lock():
            return LeaderElectionRenewResultModel(
                renewed=False,
                is_leader=False,
                leader_id=LeaderId(""),
                acquired_at=0.0,
                expires_at=0.0,
                remaining_seconds=0.0,
                message="Leader election is busy.",
            )

        try:
            record, valid = self._read_record()
            now = self._now()

            if not valid or self._is_expired(record, now):
                return LeaderElectionRenewResultModel(
                    renewed=False,
                    is_leader=False,
                    leader_id=record.leader_id,
                    acquired_at=record.acquired_at,
                    expires_at=record.expires_at,
                    remaining_seconds=self._remaining_seconds(record, now),
                    message="No active leader record.",
                )

            if record.leader_id != self._leader_id:
                return LeaderElectionRenewResultModel(
                    renewed=False,
                    is_leader=False,
                    leader_id=record.leader_id,
                    acquired_at=record.acquired_at,
                    expires_at=record.expires_at,
                    remaining_seconds=self._remaining_seconds(record, now),
                    message="Leader held by another contender.",
                )

            renewed_record = LeaderRecordModel(
                election_name=record.election_name,
                leader_id=record.leader_id,
                acquired_at=record.acquired_at,
                expires_at=now + float(self._ttl_seconds),
            )
            self._write_record_replace(renewed_record)
            remaining = self._remaining_seconds(renewed_record, now)
            return LeaderElectionRenewResultModel(
                renewed=True,
                is_leader=True,
                leader_id=renewed_record.leader_id,
                acquired_at=renewed_record.acquired_at,
                expires_at=renewed_record.expires_at,
                remaining_seconds=remaining,
                message="Leadership renewed.",
            )
        finally:
            self._release_lock()

    def release(self) -> LeaderElectionReleaseResultModel:
        """
        Release leadership if held by the caller.
        """
        if not self._acquire_lock():
            return LeaderElectionReleaseResultModel(
                released=False,
                is_leader=False,
                leader_id=LeaderId(""),
                message="Leader election is busy.",
            )

        try:
            record, valid = self._read_record()
            if not valid or record.leader_id != self._leader_id:
                return LeaderElectionReleaseResultModel(
                    released=False,
                    is_leader=False,
                    leader_id=record.leader_id,
                    message="Leader not held by caller.",
                )

            try:
                self._state_file().unlink(missing_ok=True)
            except OSError:
                return LeaderElectionReleaseResultModel(
                    released=False,
                    is_leader=True,
                    leader_id=record.leader_id,
                    message="Failed to release leader record.",
                )

            return LeaderElectionReleaseResultModel(
                released=True,
                is_leader=False,
                leader_id=LeaderId(""),
                message="Leadership released.",
            )
        finally:
            self._release_lock()

    def status(self) -> LeaderElectionStatusModel:
        """
        Retrieve the current leader status.
        """
        record, valid = self._read_record()
        now = self._now()

        if not valid or self._is_expired(record, now):
            return LeaderElectionStatusModel(
                election_name=self._election_name,
                is_leader=False,
                leader_id=LeaderId(""),
                acquired_at=0.0,
                expires_at=0.0,
                remaining_seconds=0.0,
                state_path=str(self._state_file()),
                message="No active leader.",
            )

        return LeaderElectionStatusModel(
            election_name=record.election_name,
            is_leader=record.leader_id == self._leader_id,
            leader_id=record.leader_id,
            acquired_at=record.acquired_at,
            expires_at=record.expires_at,
            remaining_seconds=self._remaining_seconds(record, now),
            state_path=str(self._state_file()),
            message="Leader record present.",
        )

    def _read_record(self) -> tuple[LeaderRecordModel, bool]:
        path = self._state_file()
        if not path.exists():
            return self._empty_record(), False

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty_record(), False

        if not isinstance(data, dict):
            return self._empty_record(), False

        election_name = CoordinationElectionName(str(data.get("election_name", "")))
        if str(election_name) != str(self._election_name):
            return self._empty_record(), False
        leader_id = LeaderId(str(data.get("leader_id", "")))
        if self._leader_id_validator is not None and not self._leader_id_validator(leader_id):
            return self._empty_record(), False
        try:
            acquired_at = float(data.get("acquired_at", 0.0))
            expires_at = float(data.get("expires_at", 0.0))
        except (TypeError, ValueError):
            return self._empty_record(), False

        return (
            LeaderRecordModel(
                election_name=election_name,
                leader_id=leader_id,
                acquired_at=acquired_at,
                expires_at=expires_at,
            ),
            True,
        )

    def _write_record_atomic(self, record: LeaderRecordModel) -> bool:
        path = self._state_file()
        payload = record.model_dump()
        encoded = json.dumps(payload).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

        try:
            fd = os.open(path, flags)
        except FileExistsError:
            return False

        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            with contextlib.suppress(OSError):
                Path(path).unlink(missing_ok=True)
            return False

        return True

    def _write_record_replace(self, record: LeaderRecordModel) -> None:
        path = self._state_file()
        payload = record.model_dump()
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp_path, path)

    def _lock_path(self) -> Path:
        return self._state_dir / f"{self._election_name}{self.LOCK_SUFFIX}"

    def _acquire_lock(self) -> bool:
        lock_path = self._lock_path()
        try:
            lock_path.mkdir()
            return True
        except FileExistsError:
            if self._is_lock_stale(lock_path):
                with contextlib.suppress(OSError):
                    lock_path.rmdir()
                try:
                    lock_path.mkdir()
                    return True
                except FileExistsError:
                    return False
            return False
        except OSError:
            return False

    def _release_lock(self) -> None:
        lock_path = self._lock_path()
        with contextlib.suppress(OSError):
            lock_path.rmdir()

    def _is_lock_stale(self, lock_path: Path) -> bool:
        try:
            mtime = lock_path.stat().st_mtime
        except OSError:
            return False
        age = self._now() - mtime
        return age > (float(self._ttl_seconds) * self.STALE_LOCK_MULTIPLIER)

    def _state_file(self) -> Path:
        filename = f"{self._election_name}.json"
        return self._state_dir / filename

    def _empty_record(self) -> LeaderRecordModel:
        return LeaderRecordModel(
            election_name=self._election_name,
            leader_id=LeaderId(""),
            acquired_at=0.0,
            expires_at=0.0,
        )

    def _new_record(self, now: float) -> LeaderRecordModel:
        return LeaderRecordModel(
            election_name=self._election_name,
            leader_id=self._leader_id,
            acquired_at=now,
            expires_at=now + float(self._ttl_seconds),
        )

    @staticmethod
    def _is_expired(record: LeaderRecordModel, now: float) -> bool:
        return record.expires_at <= now

    @staticmethod
    def _remaining_seconds(record: LeaderRecordModel, now: float) -> float:
        remaining = record.expires_at - now
        if remaining < 0:
            return 0.0
        return remaining

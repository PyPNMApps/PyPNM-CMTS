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
    ServiceGroupLeaseAcquireResultModel,
    ServiceGroupLeaseRecordModel,
    ServiceGroupLeaseReleaseResultModel,
    ServiceGroupLeaseRenewResultModel,
    ServiceGroupLeaseStatusModel,
)
from pypnm_cmts.lib.types import CoordinationElectionName, OwnerId, ServiceGroupId


class FileServiceGroupLease:
    """
    File-based service group lease using a JSON record with TTL.
    """

    LOCK_SUFFIX = ".lock"
    MIN_TTL_SECONDS = 1
    MIN_SG_ID = 0
    STALE_LOCK_MULTIPLIER = 2.0
    EMPTY_FLOAT = 0.0
    EMPTY_STR = ""
    EMPTY_INT = 0
    MESSAGE_BUSY = "Service group lease is busy."
    MESSAGE_NO_ACTIVE = "No active lease."
    MESSAGE_NOT_OWNER = "Lease held by another owner."
    MESSAGE_NOT_HELD = "Lease not held by caller."
    MESSAGE_ACQUIRED = "Lease acquired."
    MESSAGE_ALREADY_OWNER = "Already lease owner."
    MESSAGE_RENEWED = "Lease renewed."
    MESSAGE_RELEASED = "Lease released."
    MESSAGE_RELEASE_FAILED = "Failed to release lease record."
    MESSAGE_PRESENT = "Lease record present."

    def __init__(
        self,
        state_dir: Path,
        election_name: CoordinationElectionName,
        sg_id: ServiceGroupId,
        owner_id: OwnerId,
        ttl_seconds: int,
        now: Callable[[], float] | None = None,
    ) -> None:
        """
        Initialize a file-based service group lease instance.

        Args:
            state_dir (Path): Directory used to persist lease records.
            election_name (CoordinationElectionName): Logical election namespace for the lease.
            sg_id (ServiceGroupId): Service group identifier for this lease.
            owner_id (OwnerId): Lease owner identifier.
            ttl_seconds (int): Lease TTL in seconds.
            now (Callable[[], float] | None): Optional time provider for testing.
        """
        if str(election_name).strip() == "":
            raise ValueError("election_name must be non-empty.")
        if str(owner_id).strip() == "":
            raise ValueError("owner_id must be non-empty.")
        if not isinstance(sg_id, int) or isinstance(sg_id, bool):
            raise TypeError("sg_id must be an integer.")
        if int(sg_id) < self.MIN_SG_ID:
            raise ValueError("sg_id must be non-negative.")
        if int(ttl_seconds) < self.MIN_TTL_SECONDS:
            raise ValueError("ttl_seconds must be greater than zero.")

        self._state_dir = state_dir
        self._election_name = CoordinationElectionName(str(election_name).strip())
        self._sg_id = ServiceGroupId(int(sg_id))
        self._owner_id = OwnerId(str(owner_id).strip())
        self._ttl_seconds = int(ttl_seconds)
        self._now = now or time.time
        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OSError(f"Failed to create state_dir '{state_dir}'.") from exc

    def try_acquire(self) -> ServiceGroupLeaseAcquireResultModel:
        """
        Attempt to acquire the service group lease.
        """
        if not self._acquire_lock():
            return ServiceGroupLeaseAcquireResultModel(
                acquired=False,
                is_owner=False,
                sg_id=self._sg_id,
                owner_id=OwnerId(self.EMPTY_STR),
                acquired_at=self.EMPTY_FLOAT,
                expires_at=self.EMPTY_FLOAT,
                remaining_seconds=self.EMPTY_FLOAT,
                message=self.MESSAGE_BUSY,
            )

        try:
            record, valid = self._read_record()
            now = self._now()
            new_record = self._new_record(now)

            if valid and not self._is_expired(record, now):
                if record.owner_id == self._owner_id:
                    remaining = self._remaining_seconds(record, now)
                    return ServiceGroupLeaseAcquireResultModel(
                        acquired=True,
                        is_owner=True,
                        sg_id=record.sg_id,
                        owner_id=record.owner_id,
                        acquired_at=record.acquired_at,
                        expires_at=record.expires_at,
                        remaining_seconds=remaining,
                        message=self.MESSAGE_ALREADY_OWNER,
                    )
                remaining = self._remaining_seconds(record, now)
                return ServiceGroupLeaseAcquireResultModel(
                    acquired=False,
                    is_owner=False,
                    sg_id=record.sg_id,
                    owner_id=record.owner_id,
                    acquired_at=record.acquired_at,
                    expires_at=record.expires_at,
                    remaining_seconds=remaining,
                    message=self.MESSAGE_NOT_OWNER,
                )

            if valid:
                self._write_record_replace(new_record)
            else:
                acquired = self._write_record_atomic(new_record)
                if not acquired:
                    self._write_record_replace(new_record)

            remaining = self._remaining_seconds(new_record, now)
            return ServiceGroupLeaseAcquireResultModel(
                acquired=True,
                is_owner=True,
                sg_id=new_record.sg_id,
                owner_id=new_record.owner_id,
                acquired_at=new_record.acquired_at,
                expires_at=new_record.expires_at,
                remaining_seconds=remaining,
                message=self.MESSAGE_ACQUIRED,
            )
        finally:
            self._release_lock()

    def renew(self) -> ServiceGroupLeaseRenewResultModel:
        """
        Renew the service group lease TTL if held by the caller.
        """
        if not self._acquire_lock():
            return ServiceGroupLeaseRenewResultModel(
                renewed=False,
                is_owner=False,
                sg_id=self._sg_id,
                owner_id=OwnerId(self.EMPTY_STR),
                acquired_at=self.EMPTY_FLOAT,
                expires_at=self.EMPTY_FLOAT,
                remaining_seconds=self.EMPTY_FLOAT,
                message=self.MESSAGE_BUSY,
            )

        try:
            record, valid = self._read_record()
            now = self._now()

            if not valid or self._is_expired(record, now):
                return ServiceGroupLeaseRenewResultModel(
                    renewed=False,
                    is_owner=False,
                    sg_id=record.sg_id,
                    owner_id=record.owner_id,
                    acquired_at=record.acquired_at,
                    expires_at=record.expires_at,
                    remaining_seconds=self._remaining_seconds(record, now),
                    message=self.MESSAGE_NO_ACTIVE,
                )

            if record.owner_id != self._owner_id:
                return ServiceGroupLeaseRenewResultModel(
                    renewed=False,
                    is_owner=False,
                    sg_id=record.sg_id,
                    owner_id=record.owner_id,
                    acquired_at=record.acquired_at,
                    expires_at=record.expires_at,
                    remaining_seconds=self._remaining_seconds(record, now),
                    message=self.MESSAGE_NOT_OWNER,
                )

            renewed_record = ServiceGroupLeaseRecordModel(
                election_name=record.election_name,
                sg_id=record.sg_id,
                owner_id=record.owner_id,
                acquired_at=record.acquired_at,
                expires_at=now + float(self._ttl_seconds),
            )
            self._write_record_replace(renewed_record)
            remaining = self._remaining_seconds(renewed_record, now)
            return ServiceGroupLeaseRenewResultModel(
                renewed=True,
                is_owner=True,
                sg_id=renewed_record.sg_id,
                owner_id=renewed_record.owner_id,
                acquired_at=renewed_record.acquired_at,
                expires_at=renewed_record.expires_at,
                remaining_seconds=remaining,
                message=self.MESSAGE_RENEWED,
            )
        finally:
            self._release_lock()

    def release(self) -> ServiceGroupLeaseReleaseResultModel:
        """
        Release the service group lease if held by the caller.
        """
        if not self._acquire_lock():
            return ServiceGroupLeaseReleaseResultModel(
                released=False,
                is_owner=False,
                sg_id=self._sg_id,
                owner_id=OwnerId(self.EMPTY_STR),
                message=self.MESSAGE_BUSY,
            )

        try:
            record, valid = self._read_record()
            if not valid or record.owner_id != self._owner_id:
                return ServiceGroupLeaseReleaseResultModel(
                    released=False,
                    is_owner=False,
                    sg_id=record.sg_id,
                    owner_id=record.owner_id,
                    message=self.MESSAGE_NOT_HELD,
                )

            try:
                self._state_file().unlink(missing_ok=True)
            except OSError:
                return ServiceGroupLeaseReleaseResultModel(
                    released=False,
                    is_owner=True,
                    sg_id=record.sg_id,
                    owner_id=record.owner_id,
                    message=self.MESSAGE_RELEASE_FAILED,
                )

            return ServiceGroupLeaseReleaseResultModel(
                released=True,
                is_owner=False,
                sg_id=self._sg_id,
                owner_id=OwnerId(self.EMPTY_STR),
                message=self.MESSAGE_RELEASED,
            )
        finally:
            self._release_lock()

    def status(self) -> ServiceGroupLeaseStatusModel:
        """
        Retrieve the current service group lease status.
        """
        record, valid = self._read_record()
        now = self._now()

        if not valid or self._is_expired(record, now):
            return ServiceGroupLeaseStatusModel(
                election_name=self._election_name,
                sg_id=self._sg_id,
                is_owner=False,
                owner_id=OwnerId(self.EMPTY_STR),
                acquired_at=self.EMPTY_FLOAT,
                expires_at=self.EMPTY_FLOAT,
                remaining_seconds=self.EMPTY_FLOAT,
                state_path=str(self._state_file()),
                message=self.MESSAGE_NO_ACTIVE,
            )

        return ServiceGroupLeaseStatusModel(
            election_name=record.election_name,
            sg_id=record.sg_id,
            is_owner=record.owner_id == self._owner_id,
            owner_id=record.owner_id,
            acquired_at=record.acquired_at,
            expires_at=record.expires_at,
            remaining_seconds=self._remaining_seconds(record, now),
            state_path=str(self._state_file()),
            message=self.MESSAGE_PRESENT,
        )

    def _read_record(self) -> tuple[ServiceGroupLeaseRecordModel, bool]:
        path = self._state_file()
        if not path.exists():
            return self._empty_record(), False

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty_record(), False

        if not isinstance(data, dict):
            return self._empty_record(), False

        election_name = CoordinationElectionName(str(data.get("election_name", self.EMPTY_STR)))
        if str(election_name) != str(self._election_name):
            return self._empty_record(), False

        try:
            sg_id = int(data.get("sg_id", self.EMPTY_INT))
        except (TypeError, ValueError):
            return self._empty_record(), False

        if sg_id != int(self._sg_id):
            return self._empty_record(), False

        owner_id = OwnerId(str(data.get("owner_id", self.EMPTY_STR)))

        try:
            acquired_at = float(data.get("acquired_at", self.EMPTY_FLOAT))
            expires_at = float(data.get("expires_at", self.EMPTY_FLOAT))
        except (TypeError, ValueError):
            return self._empty_record(), False

        return (
            ServiceGroupLeaseRecordModel(
                election_name=election_name,
                sg_id=ServiceGroupId(sg_id),
                owner_id=owner_id,
                acquired_at=acquired_at,
                expires_at=expires_at,
            ),
            True,
        )

    def _write_record_atomic(self, record: ServiceGroupLeaseRecordModel) -> bool:
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

    def _write_record_replace(self, record: ServiceGroupLeaseRecordModel) -> None:
        path = self._state_file()
        payload = record.model_dump()
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp_path, path)
        except OSError:
            return

    def _lock_path(self) -> Path:
        return self._state_dir / f"{self._election_name}.sg-{self._sg_id}{self.LOCK_SUFFIX}"

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
        filename = f"{self._election_name}.sg-{self._sg_id}.json"
        return self._state_dir / filename

    def _empty_record(self) -> ServiceGroupLeaseRecordModel:
        return ServiceGroupLeaseRecordModel(
            election_name=self._election_name,
            sg_id=self._sg_id,
            owner_id=OwnerId(self.EMPTY_STR),
            acquired_at=self.EMPTY_FLOAT,
            expires_at=self.EMPTY_FLOAT,
        )

    def _new_record(self, now: float) -> ServiceGroupLeaseRecordModel:
        return ServiceGroupLeaseRecordModel(
            election_name=self._election_name,
            sg_id=self._sg_id,
            owner_id=self._owner_id,
            acquired_at=now,
            expires_at=now + float(self._ttl_seconds),
        )

    @staticmethod
    def _is_expired(record: ServiceGroupLeaseRecordModel, now: float) -> bool:
        return record.expires_at <= now

    @staticmethod
    def _remaining_seconds(record: ServiceGroupLeaseRecordModel, now: float) -> float:
        remaining = record.expires_at - now
        if remaining < 0:
            return 0.0
        return remaining

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import socket
from pathlib import Path

from pypnm_cmts.lib.types import OwnerId

DEFAULT_OWNER_ID: OwnerId = OwnerId("unknown")
OWNER_ID_FILENAME = "owner_id.txt"


class OwnerIdResolver:
    """
    Resolve a stable OwnerId for coordination sharding and leases.

    Resolution order:
    1) Explicit owner id (if provided and non-empty).
    2) Hostname derived owner id.
    3) DEFAULT_OWNER_ID.
    """

    @staticmethod
    def resolve(explicit_owner_id: str | None, state_dir: Path | None) -> OwnerId:
        """
        Resolve a stable OwnerId from explicit input, persisted storage, or hostname.

        Args:
            explicit_owner_id (str | None): Optional explicit owner id override.
            state_dir (Path | None): Optional state directory for persistence.

        Returns:
            OwnerId: Resolved owner id.
        """
        if explicit_owner_id is not None:
            owner_value = explicit_owner_id.strip()
            if owner_value != "":
                return OwnerId(owner_value)

        derived = OwnerIdResolver._derive_owner_id()
        return derived

    @staticmethod
    def _read_owner_id(state_dir: Path) -> OwnerId | None:
        try:
            path = state_dir / OWNER_ID_FILENAME
            if not path.exists():
                return None
            content = path.read_text(encoding="utf-8").strip()
            if content == "":
                return None
            return OwnerId(content)
        except Exception:
            return

    @staticmethod
    def _write_owner_id(state_dir: Path, owner_id: OwnerId) -> None:
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            path = state_dir / OWNER_ID_FILENAME
            path.write_text(str(owner_id), encoding="utf-8")
        except Exception:
            return

    @staticmethod
    def _derive_owner_id() -> OwnerId:
        try:
            hostname = socket.gethostname().strip()
        except Exception:
            hostname = ""
        if hostname == "":
            return DEFAULT_OWNER_ID
        return OwnerId(hostname)


__all__ = [
    "OwnerIdResolver",
    "DEFAULT_OWNER_ID",
    "OWNER_ID_FILENAME",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pypnm_cmts.config.owner_id_resolver import OwnerIdResolver
from pypnm_cmts.lib.types import OwnerId


def test_owner_id_resolver_prefers_explicit_value(tmp_path: Path) -> None:
    resolved = OwnerIdResolver.resolve("explicit-owner", tmp_path)

    assert resolved == OwnerId("explicit-owner")


def test_owner_id_resolver_derives_hostname(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr("pypnm_cmts.config.owner_id_resolver.socket.gethostname", lambda: "host-a")

    resolved = OwnerIdResolver.resolve("", tmp_path)

    assert resolved == OwnerId("host-a")

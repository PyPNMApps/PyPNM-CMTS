# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pypnm_cmts.config.owner_id_resolver import OwnerIdResolver
from pypnm_cmts.lib.types import OwnerId


def test_owner_id_resolver_prefers_explicit_value(tmp_path: Path) -> None:
    owner_file = tmp_path / "owner_id.txt"
    owner_file.write_text("persisted", encoding="utf-8")

    resolved = OwnerIdResolver.resolve("explicit-owner", tmp_path)

    assert resolved == OwnerId("explicit-owner")


def test_owner_id_resolver_uses_persisted_value(tmp_path: Path) -> None:
    owner_file = tmp_path / "owner_id.txt"
    owner_file.write_text("persisted-owner", encoding="utf-8")

    resolved = OwnerIdResolver.resolve("", tmp_path)

    assert resolved == OwnerId("persisted-owner")


def test_owner_id_resolver_derives_and_persists(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr("pypnm_cmts.config.owner_id_resolver.socket.gethostname", lambda: "host-a")

    resolved = OwnerIdResolver.resolve("", tmp_path)
    owner_file = tmp_path / "owner_id.txt"

    assert resolved == OwnerId("host-a")
    assert owner_file.exists()
    assert owner_file.read_text(encoding="utf-8").strip() == "host-a"

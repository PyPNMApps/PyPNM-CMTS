# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.pidfile_manager import PidFileRecord


def test_pidfile_written_and_removed_controller(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.getpid", lambda: 12345)
    record = PidFileRecord.for_controller(tmp_path)
    with record:
        assert record.pidfile_path.exists()
        assert record.pidfile_path.read_text(encoding="utf-8").strip() == "12345"
    assert not record.pidfile_path.exists()


def test_pidfile_written_worker_with_sg_id(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.getpid", lambda: 22222)
    record = PidFileRecord.for_worker(tmp_path, ServiceGroupId(7))
    with record:
        assert record.pidfile_path.exists()
        assert record.pidfile_path.read_text(encoding="utf-8").strip() == "22222"
    assert not record.pidfile_path.exists()


def test_pidfile_cleanup_best_effort_does_not_raise(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    record = PidFileRecord.for_controller(tmp_path)
    with record:
        assert record.pidfile_path.exists()

    def _raise_unlink(self: Path) -> None:
        raise OSError("unlink failed")

    record.pidfile_path.write_text("999\n", encoding="utf-8")
    monkeypatch.setattr(Path, "unlink", _raise_unlink)
    record.__exit__(None, None, None)
    assert record.pidfile_path.exists()

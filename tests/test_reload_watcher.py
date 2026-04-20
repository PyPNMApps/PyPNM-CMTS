# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pathlib import Path

import pytest

from pypnm_cmts.support import reload_watcher


@pytest.mark.unit
def test_read_reload_watcher_pid_invalid_payload_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pidfile_path = tmp_path / "coordination" / "watcher.pid"
    pidfile_path.parent.mkdir(parents=True, exist_ok=True)
    pidfile_path.write_text("not-a-pid\n", encoding="utf-8")

    monkeypatch.setattr(reload_watcher, "resolve_reload_watcher_pidfile_path", lambda: pidfile_path)

    assert reload_watcher.read_reload_watcher_pid() is None


@pytest.mark.unit
def test_ensure_reload_watcher_reuses_running_pidfile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pidfile_path = tmp_path / "coordination" / "watcher.pid"
    pidfile_path.parent.mkdir(parents=True, exist_ok=True)
    pidfile_path.write_text("4321\n", encoding="utf-8")

    popen_calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, command: list[str], **_: object) -> None:
            popen_calls.append(command)

    monkeypatch.setattr(reload_watcher, "resolve_reload_watcher_pidfile_path", lambda: pidfile_path)
    monkeypatch.setattr(reload_watcher, "is_process_running", lambda pid: pid == 4321)
    monkeypatch.setattr(reload_watcher.subprocess, "Popen", _FakePopen)

    started, returned_pidfile = reload_watcher.ensure_reload_watcher(project_root=tmp_path, python_executable="/usr/bin/python3")

    assert started is False
    assert returned_pidfile == pidfile_path
    assert popen_calls == []


@pytest.mark.unit
def test_ensure_reload_watcher_starts_detached_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pidfile_path = tmp_path / "coordination" / "watcher.pid"
    sentinel_path = tmp_path / "coordination" / "webservice.reload"
    popen_calls: list[tuple[list[str], dict[str, object]]] = []

    class _FakePopen:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            popen_calls.append((command, kwargs))

    monkeypatch.setattr(reload_watcher, "resolve_reload_watcher_pidfile_path", lambda: pidfile_path)
    monkeypatch.setattr(reload_watcher, "resolve_reload_sentinel_path", lambda: sentinel_path)
    monkeypatch.setattr(reload_watcher, "read_reload_watcher_pid", lambda _path=None: None)
    monkeypatch.setattr(reload_watcher.subprocess, "Popen", _FakePopen)

    started, returned_pidfile = reload_watcher.ensure_reload_watcher(
        project_root=tmp_path,
        python_executable="/usr/bin/python3",
    )

    assert started is True
    assert returned_pidfile == pidfile_path
    assert len(popen_calls) == 1
    command, kwargs = popen_calls[0]
    assert command[:2] == ["/usr/bin/python3", str(tmp_path / "tools" / "support" / "watch_reload_sentinel.py")]
    assert "--sentinel" in command
    assert str(sentinel_path) in command
    assert "--pidfile" in command
    assert str(pidfile_path) in command
    restart_cmd = command[command.index("--restart-cmd") + 1]
    assert "restart_from_launch_state.py" in restart_cmd
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["start_new_session"] is True

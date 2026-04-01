# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pathlib import Path

import pytest

from pypnm_cmts.support import serve_launch_state


@pytest.mark.unit
def test_write_and_read_launch_state_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "runtime" / "pypnm-cmts-serve-launch.json"
    monkeypatch.setattr(serve_launch_state, "resolve_launch_state_path", lambda: state_path)

    state = serve_launch_state.build_launch_state(
        executable="/usr/bin/python3",
        argv=["-m", "pypnm_cmts.cli", "serve", "--host", "127.0.0.1"],
    )
    written = serve_launch_state.write_launch_state(state)

    assert written == state_path
    assert state_path.exists()

    loaded = serve_launch_state.read_launch_state()
    assert loaded.schema_version == serve_launch_state.LAUNCH_STATE_SCHEMA_VERSION
    assert loaded.executable == str(Path("/usr/bin/python3").resolve())
    assert loaded.argv == ["-m", "pypnm_cmts.cli", "serve", "--host", "127.0.0.1"]
    assert loaded.launch_cwd != ""
    assert loaded.pid > 0
    assert "PATH" in loaded.env
    assert loaded.recorded_at_utc != ""

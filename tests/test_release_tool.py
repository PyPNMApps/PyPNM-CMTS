# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pypnm_cmts.tools import release_tool


def _write_version_files(root: Path, version: str) -> None:
    version_path = root / "src" / "pypnm_cmts" / "version.py"
    pyproject_path = root / "pyproject.toml"
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(
        "from __future__ import annotations\n\n__all__ = [\"__version__\"]\n\n__version__: str = \""
        + version
        + "\"\n",
        encoding="utf-8",
    )
    pyproject_path.write_text(
        "[project]\nname = \"pypnm-docsis-cmts\"\nversion = \""
        + version
        + "\"\n",
        encoding="utf-8",
    )


def test_release_tool_dry_run_skips_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_version_files(tmp_path, "0.1.2.3")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(release_tool, "VERSION_FILE_PATH", Path("src/pypnm_cmts/version.py"))
    monkeypatch.setattr(release_tool, "PYPROJECT_PATH", Path("pyproject.toml"))

    def _reject_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run should not be invoked during dry-run")

    monkeypatch.setattr(subprocess, "run", _reject_run)

    options = release_tool.ReleaseTool._build_parser().parse_args(["--bump-ga", "--dry-run"])
    assert release_tool.ReleaseTool.run(options) == 0


def test_release_tool_executes_release_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_version_files(tmp_path, "0.1.2.3")
    runner_path = tmp_path / "tools" / "release" / "test-runner.py"
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text("# stub", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(release_tool, "VERSION_FILE_PATH", Path("src/pypnm_cmts/version.py"))
    monkeypatch.setattr(release_tool, "PYPROJECT_PATH", Path("pyproject.toml"))
    monkeypatch.setattr(release_tool, "RELEASE_TEST_RUNNER", Path("tools/release/test-runner.py"))

    calls: list[list[str]] = []

    def _fake_run(
        cmd: list[str],
        check: bool = False,
        text: bool | None = None,
        capture_output: bool = False,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        _ = text
        _ = capture_output
        _ = cwd
        _ = env
        calls.append(cmd)
        if cmd[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    options = release_tool.ReleaseTool._build_parser().parse_args(["--bump-ga"])
    assert release_tool.ReleaseTool.run(options) == 0

    version_path = tmp_path / "src" / "pypnm_cmts" / "version.py"
    assert "0.1.3.0" in version_path.read_text(encoding="utf-8")

    joined = [" ".join(cmd) for cmd in calls]
    assert any("tools/release/test-runner.py" in cmd for cmd in joined)
    assert any(cmd.startswith("git add") for cmd in joined)
    assert any(cmd.startswith("git commit") for cmd in joined)
    assert any(cmd.startswith("git tag v0.1.3.0") for cmd in joined)
    assert any(cmd.startswith("git push origin main") for cmd in joined)
    assert any(cmd.startswith("git push origin v0.1.3.0") for cmd in joined)

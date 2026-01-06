# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from types import TracebackType

import pytest

from pypnm_cmts.tools.publish_tool import PublishTool


class _RunCapture:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.envs: list[dict[str, str] | None] = []

    def __call__(
        self,
        cmd: list[str],
        check: bool = False,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        _ = cwd
        self.commands.append(cmd)
        self.envs.append(env)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def _make_artifact(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "pypnm_docsis_cmts-0.1.0.0.tar.gz").write_text("stub", encoding="utf-8")

def _write_pyproject(tmp_path: Path, version: str = "0.1.0.0") -> None:
    (tmp_path / "pyproject.toml").write_text(
        f"[project]\nversion = \"{version}\"\n",
        encoding="utf-8",
    )

def _mock_urlopen(payload: str) -> object:
    class _Response:
        def __init__(self, text: str) -> None:
            self._text = text

        def __enter__(self) -> io.StringIO:
            return io.StringIO(self._text)

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            _ = exc_type
            _ = exc
            _ = traceback

    return _Response(payload)


@pytest.mark.unit
def test_publish_tool_uses_env_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)
    monkeypatch.setenv("PYPI_API_TOKEN", "token-value")

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {}}"),
    )

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check", "--yes"])
    assert PublishTool.run(options) == 0

    assert any("twine" in cmd for cmd in capture.commands)
    assert capture.envs
    upload_env = capture.envs[-1]
    assert upload_env is not None
    assert upload_env.get("TWINE_USERNAME") == "__token__"
    assert upload_env.get("TWINE_PASSWORD") == "token-value"


@pytest.mark.unit
def test_publish_tool_dry_run_skips_upload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {}}"),
    )

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check", "--dry-run"])
    assert PublishTool.run(options) == 0

    assert all("upload" not in cmd for cmd in capture.commands)


@pytest.mark.unit
def test_publish_tool_prompts_for_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)
    monkeypatch.delenv("PYPI_API_TOKEN", raising=False)

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {}}"),
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("pypnm_cmts.tools.publish_tool.getpass", lambda _prompt: "prompt-token")

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check", "--yes"])
    assert PublishTool.run(options) == 0

    assert capture.envs
    upload_env = capture.envs[-1]
    assert upload_env is not None
    assert upload_env.get("TWINE_PASSWORD") == "prompt-token"


@pytest.mark.unit
def test_publish_tool_build_and_check_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {}}"),
    )

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--dry-run"])
    assert PublishTool.run(options) == 0

    joined = [" ".join(cmd) for cmd in capture.commands]
    assert any("-m build" in cmd for cmd in joined)
    assert any("-m twine check" in cmd for cmd in joined)
    assert all("-m twine upload" not in cmd for cmd in joined)


@pytest.mark.unit
def test_publish_tool_skips_existing_version(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)
    monkeypatch.setenv("PYPI_API_TOKEN", "token-value")
    monkeypatch.setattr(subprocess, "run", _RunCapture())
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {\"0.1.0.0\": [{}]}}"),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check"])
    assert PublishTool.run(options) == 0


@pytest.mark.unit
def test_publish_tool_force_overrides_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)
    monkeypatch.setenv("PYPI_API_TOKEN", "token-value")

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {\"0.1.0.0\": [{}]}}"),
    )

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check", "--force", "--yes"])
    assert PublishTool.run(options) == 0

    assert any("upload" in cmd for cmd in capture.commands)


@pytest.mark.unit
def test_publish_tool_declines_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {}}"),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check"])
    assert PublishTool.run(options) == 0

    assert all("upload" not in cmd for cmd in capture.commands)


@pytest.mark.unit
def test_publish_tool_yes_skips_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _make_artifact(tmp_path)
    _write_pyproject(tmp_path)
    monkeypatch.setenv("PYPI_API_TOKEN", "token-value")

    capture = _RunCapture()
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(
        "pypnm_cmts.tools.publish_tool.urllib.request.urlopen",
        lambda _url: _mock_urlopen("{\"releases\": {}}"),
    )

    parser = PublishTool._build_parser()
    options = parser.parse_args(["--skip-build", "--skip-check", "--yes"])
    assert PublishTool.run(options) == 0

    assert any("upload" in cmd for cmd in capture.commands)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import importlib.util
import types
from pathlib import Path

import pytest

CHECK_VERSION_PATH = Path("tools/release/check_version.py")
TEST_RUNNER_PATH = Path("tools/release/test-runner.py")


def _load_tool_module(path: Path, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_check_version_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    check_version = _load_tool_module(CHECK_VERSION_PATH, "check_version")
    version_path = tmp_path / "src/pypnm_cmts/version.py"
    pyproject_path = tmp_path / "pyproject.toml"
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text('__version__: str = "1.2.3.0"\n', encoding="utf-8")
    pyproject_path.write_text('version = "1.2.3.1"\n', encoding="utf-8")

    monkeypatch.setattr(check_version.VersionCheckTool, "_find_project_root", staticmethod(lambda _: tmp_path))

    options = argparse.Namespace(json=False)
    result = check_version.VersionCheckTool.run(options)

    assert result == check_version.VersionCheckTool.EXIT_MISMATCH


@pytest.mark.unit
def test_release_test_runner_builds_default_commands() -> None:
    test_runner = _load_tool_module(TEST_RUNNER_PATH, "test_runner")
    parser = test_runner._build_parser()
    options = parser.parse_args([])
    commands = test_runner._build_commands(options)
    labels = [label for label, _cmd in commands]

    assert labels == [
        "ruff check",
        "pytest",
        "mkdocs build",
        "python -m build",
        "twine check",
    ]


@pytest.mark.unit
def test_release_test_runner_skip_all() -> None:
    test_runner = _load_tool_module(TEST_RUNNER_PATH, "test_runner")
    parser = test_runner._build_parser()
    options = parser.parse_args(
        [
            "--skip-ruff",
            "--skip-tests",
            "--skip-docs",
            "--skip-build",
            "--skip-twine",
        ]
    )
    commands = test_runner._build_commands(options)

    assert commands == []

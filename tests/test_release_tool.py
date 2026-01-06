# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from pypnm_cmts.tools import release_tool
from pypnm_cmts.tools.release_tool import ReleaseTool


@pytest.mark.unit
def test_parse_version_valid() -> None:
    assert ReleaseTool.parse_version("1.2.3.4") == (1, 2, 3, 4)


@pytest.mark.unit
def test_parse_version_invalid() -> None:
    with pytest.raises(ValueError):
        ReleaseTool.parse_version("1.2.3")
    with pytest.raises(ValueError):
        ReleaseTool.parse_version("1.2.x.4")


@pytest.mark.unit
def test_ga_vs_hotfix() -> None:
    assert ReleaseTool.is_ga((1, 2, 3, 0)) is True
    assert ReleaseTool.is_ga((1, 2, 3, 1)) is False


@pytest.mark.unit
def test_bump_ga_patch() -> None:
    assert ReleaseTool.bump_ga((1, 2, 3, 4), "patch") == (1, 2, 4, 0)


@pytest.mark.unit
def test_bump_hotfix_build() -> None:
    assert ReleaseTool.bump_hotfix_build((1, 2, 3, 0)) == (1, 2, 3, 1)
    assert ReleaseTool.bump_hotfix_build((1, 2, 3, 2)) == (1, 2, 3, 3)


@pytest.mark.unit
def test_dry_run_does_not_modify_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    version_path = tmp_path / "version.py"
    pyproject_path = tmp_path / "pyproject.toml"
    version_path.write_text('__version__: str = "1.2.3.0"\n', encoding="utf-8")
    pyproject_path.write_text('version = "1.2.3.0"\n', encoding="utf-8")

    monkeypatch.setattr(release_tool, "VERSION_FILE_PATH", version_path)
    monkeypatch.setattr(release_tool, "PYPROJECT_PATH", pyproject_path)

    options = argparse.Namespace(
        bump_ga=True,
        bump_hot_fix=False,
        major=False,
        minor=False,
        patch=True,
        tag=False,
        dry_run=True,
    )

    ReleaseTool.run(options)

    assert version_path.read_text(encoding="utf-8").strip() == '__version__: str = "1.2.3.0"'
    assert pyproject_path.read_text(encoding="utf-8").strip() == 'version = "1.2.3.0"'

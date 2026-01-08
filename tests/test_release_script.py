# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


def _load_release_script() -> object:
    script_path = Path(__file__).resolve().parents[1] / "tools" / "release" / "release.py"
    spec = importlib.util.spec_from_file_location("release_script", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load release script from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release_script = _load_release_script()


def test_release_branch_check_allows_main(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout="main\n", stderr="")

    monkeypatch.setattr(release_script, "_run", _fake_run)
    release_script._ensure_release_branch()


def test_release_branch_check_rejects_feature_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout="feature/foo\n", stderr="")

    monkeypatch.setattr(release_script, "_run", _fake_run)
    with pytest.raises(SystemExit):
        release_script._ensure_release_branch()

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import subprocess

import pytest

from tools.release import release as release_script


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

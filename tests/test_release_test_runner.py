# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_release_test_runner_accepts_ruff_fix() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "tools" / "release" / "test-runner.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--ruff-fix",
            "--skip-ruff",
            "--skip-tests",
            "--skip-docs",
            "--skip-build",
            "--skip-twine",
        ],
        check=False,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Release verification completed successfully." in result.stdout

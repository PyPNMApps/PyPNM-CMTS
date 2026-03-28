# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _run_install(script_path: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script_path), *args],
        check=False,
        cwd=script_path.parent,
        env=env,
        text=True,
        capture_output=True,
    )


def test_install_script_help() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "install.sh"
    env = os.environ.copy()
    env["PYPNM_CMTS_INSTALL_TEST"] = "1"
    result = _run_install(script_path, ["--help"], env)
    assert result.returncode == 0
    assert "PyPNM-CMTS Installer" in result.stdout


def test_install_script_development_mode_creates_and_removes_venv(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "install.sh"
    venv_dir = tmp_path / "venv-test"
    env = os.environ.copy()
    env["PYPNM_CMTS_INSTALL_TEST"] = "1"
    env["PYPNM_CMTS_INSTALL_TEST_CREATE_VENV"] = "1"
    result = _run_install(script_path, ["--development", str(venv_dir)], env)
    assert result.returncode == 0
    assert "PYPNM_CMTS_INSTALL_TEST_MODE=development" in result.stdout
    assert f"PYPNM_CMTS_INSTALL_TEST_VENV_DIR={venv_dir}" in result.stdout
    assert not venv_dir.exists()


def test_install_script_update_ga_mode() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "install.sh"
    env = os.environ.copy()
    env["PYPNM_CMTS_INSTALL_TEST"] = "1"
    result = _run_install(script_path, ["--update-ga", "v0.1.2.3"], env)
    assert result.returncode == 0
    assert "PYPNM_CMTS_INSTALL_TEST_MODE=update-ga" in result.stdout


def test_install_script_update_development_pypnm_docsis_mode() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "install.sh"
    env = os.environ.copy()
    env["PYPNM_CMTS_INSTALL_TEST"] = "1"
    result = _run_install(script_path, ["--update-development-pypnm-docsis"], env)
    assert result.returncode == 0
    assert "PYPNM_CMTS_INSTALL_TEST_MODE=update-development-pypnm-docsis" in result.stdout
    assert "PYPNM_CMTS_INSTALL_TEST_PYPNM_DOCSIS_TAG=" not in result.stdout


def test_install_script_update_development_pypnm_docsis_mode_with_tag() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "install.sh"
    env = os.environ.copy()
    env["PYPNM_CMTS_INSTALL_TEST"] = "1"
    result = _run_install(script_path, ["--update-development-pypnm-docsis", "v1.4.2.0"], env)
    assert result.returncode == 0
    assert "PYPNM_CMTS_INSTALL_TEST_MODE=update-development-pypnm-docsis" in result.stdout
    assert "PYPNM_CMTS_INSTALL_TEST_PYPNM_DOCSIS_TAG=v1.4.2.0" in result.stdout


def test_install_script_fallback_installs_full_docs_toolchain() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "install.sh"
    script_text = script_path.read_text(encoding="utf-8")

    expected_packages = "pytest mkdocs mkdocs-material mkdocs-mermaid2-plugin pymdown-extensions"
    assert script_text.count(expected_packages) == 2

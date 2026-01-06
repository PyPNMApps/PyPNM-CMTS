#!/usr/bin/env python3
from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = REPO_ROOT / "dist"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local CI parity checks.")
    parser.add_argument("--skip-ruff", action="store_true", help="Skip ruff check.")
    parser.add_argument("--ruff-fix", action="store_true", help="Run ruff check with --fix.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest.")
    parser.add_argument("--skip-docs", action="store_true", help="Skip mkdocs build.")
    parser.add_argument("--skip-build", action="store_true", help="Skip python -m build.")
    parser.add_argument("--skip-twine", action="store_true", help="Skip twine check.")
    parser.add_argument("--no-color", action="store_true", help="Disable color output.")
    return parser


def _build_twine_command(artifacts: list[Path]) -> list[str]:
    command = [sys.executable, "-m", "twine", "check"]
    command.extend([str(path) for path in artifacts])
    return command


def _build_commands(options: argparse.Namespace) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = []
    if not options.skip_ruff:
        ruff_command = [sys.executable, "-m", "ruff", "check", "."]
        ruff_label = "ruff check"
        if options.ruff_fix:
            ruff_command.append("--fix")
            ruff_label = "ruff check --fix"
        commands.append((ruff_label, ruff_command))
    if not options.skip_tests:
        commands.append(("pytest", [sys.executable, "-m", "pytest", "-q", "-ra", "--tb=short"]))
    if not options.skip_docs:
        commands.append(("mkdocs build", [sys.executable, "-m", "mkdocs", "build", "--strict"]))
    if not options.skip_build:
        commands.append(("python -m build", [sys.executable, "-m", "build"]))
    if not options.skip_twine:
        commands.append(("twine check", _build_twine_command([])))
    return commands


def _run(cmd: list[str], label: str, env: dict[str, str]) -> None:
    print(f"[release-test] {label}")
    result = subprocess.run(cmd, check=False, cwd=REPO_ROOT, env=env)
    if result.returncode != 0:
        print(f"[release-test] {label} failed with exit code {result.returncode}", file=sys.stderr)
        raise SystemExit(result.returncode)


def main() -> int:
    """
    Run the local release verification sequence.

    Sequence:
      - ruff check
      - pytest -q -ra --tb=short
      - mkdocs build --strict
      - python -m build
      - python -m twine check dist/*
    """
    parser = _build_parser()
    options = parser.parse_args()
    env = dict(os.environ)
    if options.no_color:
        env["NO_COLOR"] = "1"

    commands = _build_commands(options)
    for label, cmd in commands:
        if label == "twine check":
            artifacts = sorted(DIST_DIR.glob("*"))
            if not artifacts:
                print(f"[release-test] dist directory empty at {DIST_DIR}", file=sys.stderr)
                return 1
            cmd = _build_twine_command(artifacts)
        _run(cmd, label, env)
    print("[release-test] Release verification completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

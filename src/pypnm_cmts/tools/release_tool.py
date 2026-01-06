# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


VERSION_FILE_PATH = Path("src/pypnm_cmts/version.py")
PYPROJECT_PATH = Path("pyproject.toml")
VERSION_PATTERN = re.compile(r'^__version__\s*:\s*str\s*=\s*"([^"]+)"', re.MULTILINE)
PYPROJECT_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
RELEASE_TEST_RUNNER = Path("tools/release/test-runner.py")
RELEASE_COMMIT_TEMPLATE = "Release v{version}"

VERSION_PARTS = 4
BUILD_INDEX = 3


class ReleaseTool:
    """Release helper for PyPNM-CMTS versioning and tagging."""

    @staticmethod
    def parse_version(version: str) -> tuple[int, int, int, int]:
        parts = version.strip().split(".")
        if len(parts) != VERSION_PARTS:
            raise ValueError("Version must use MAJOR.MINOR.PATCH.BUILD format.")
        numbers: list[int] = []
        for part in parts:
            if not part.isdigit():
                raise ValueError("Version parts must be numeric.")
            numbers.append(int(part))
        return (numbers[0], numbers[1], numbers[2], numbers[3])

    @staticmethod
    def format_version(parts: tuple[int, int, int, int]) -> str:
        return ".".join(str(part) for part in parts)

    @staticmethod
    def is_ga(parts: tuple[int, int, int, int]) -> bool:
        return int(parts[BUILD_INDEX]) == 0

    @staticmethod
    def bump_ga(parts: tuple[int, int, int, int], bump_kind: str) -> tuple[int, int, int, int]:
        major, minor, patch, _build = parts
        if bump_kind == "major":
            return (major + 1, 0, 0, 0)
        if bump_kind == "minor":
            return (major, minor + 1, 0, 0)
        if bump_kind == "patch":
            return (major, minor, patch + 1, 0)
        raise ValueError("bump_kind must be major, minor, or patch.")

    @staticmethod
    def bump_hotfix(parts: tuple[int, int, int, int], bump_kind: str) -> tuple[int, int, int, int]:
        major, minor, patch, _build = parts
        if bump_kind == "major":
            return (major + 1, 0, 0, 1)
        if bump_kind == "minor":
            return (major, minor + 1, 0, 1)
        if bump_kind == "patch":
            return (major, minor, patch + 1, 1)
        raise ValueError("bump_kind must be major, minor, or patch.")

    @staticmethod
    def bump_hotfix_build(parts: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        major, minor, patch, build = parts
        if int(build) <= 0:
            return (major, minor, patch, 1)
        return (major, minor, patch, build + 1)

    @staticmethod
    def read_version_file(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        match = VERSION_PATTERN.search(text)
        if not match:
            raise ValueError(f"Unable to locate __version__ in {path}.")
        return match.group(1)

    @staticmethod
    def read_pyproject_version(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        match = PYPROJECT_VERSION_PATTERN.search(text)
        if not match:
            raise ValueError(f"Unable to locate version in {path}.")
        return match.group(1)

    @staticmethod
    def write_version_file(path: Path, version: str) -> None:
        text = path.read_text(encoding="utf-8")
        updated = VERSION_PATTERN.sub(f'__version__: str = "{version}"', text)
        path.write_text(updated, encoding="utf-8")

    @staticmethod
    def write_pyproject_version(path: Path, version: str) -> None:
        text = path.read_text(encoding="utf-8")
        updated = PYPROJECT_VERSION_PATTERN.sub(f'version = "{version}"', text)
        path.write_text(updated, encoding="utf-8")

    @staticmethod
    def ensure_git_clean() -> None:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            text=True,
            capture_output=True,
            check=False,
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            raise RuntimeError("Git status failed; ensure this is a git repository.")
        if (result.stdout or "").strip():
            raise RuntimeError("Working tree is not clean; commit or stash changes first.")

    @staticmethod
    def _resolve_current_branch() -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            raise RuntimeError("Unable to resolve current git branch.")
        branch = (result.stdout or "").strip()
        if branch == "" or branch == "HEAD":
            raise RuntimeError("Detached HEAD; checkout a branch before releasing.")
        return branch

    @staticmethod
    def _run_release_tests() -> None:
        if not RELEASE_TEST_RUNNER.exists():
            raise RuntimeError(f"Release test runner not found: {RELEASE_TEST_RUNNER}")
        subprocess.run(
            [sys.executable, str(RELEASE_TEST_RUNNER)],
            check=True,
            cwd=Path.cwd(),
        )

    @staticmethod
    def _cleanup_release_artifacts() -> None:
        targets = [
            Path("dist"),
            Path("build"),
            Path(".pytest_cache"),
            Path(".ruff_cache"),
            Path(".mypy_cache"),
            Path(".pyright"),
            Path(".coverage"),
        ]
        for target in targets:
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink(missing_ok=True)
        for path in Path.cwd().glob("*.egg-info"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def _commit_release(version: str) -> None:
        message = RELEASE_COMMIT_TEMPLATE.format(version=version)
        subprocess.run(
            ["git", "add", str(VERSION_FILE_PATH), str(PYPROJECT_PATH)],
            check=True,
            cwd=Path.cwd(),
        )
        subprocess.run(["git", "commit", "-m", message], check=True, cwd=Path.cwd())

    @staticmethod
    def _tag_release(tag: str) -> None:
        subprocess.run(["git", "tag", tag], check=True, cwd=Path.cwd())

    @classmethod
    def _push_release(cls, tag: str) -> None:
        branch = cls._resolve_current_branch()
        subprocess.run(["git", "push", "origin", branch], check=True, cwd=Path.cwd())
        subprocess.run(["git", "push", "origin", tag], check=True, cwd=Path.cwd())

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="PyPNM-CMTS release helper.")
        bump_group = parser.add_mutually_exclusive_group(required=True)
        bump_group.add_argument("--bump-ga", action="store_true", help="Create a GA release (BUILD=0).")
        bump_group.add_argument("--bump-hot-fix", action="store_true", help="Create a hot-fix release (BUILD>0).")
        parser.add_argument(
            "--major",
            action="store_true",
            help="Bump major version (resets minor/patch).",
        )
        parser.add_argument(
            "--minor",
            action="store_true",
            help="Bump minor version (resets patch).",
        )
        parser.add_argument(
            "--patch",
            action="store_true",
            help="Bump patch version (default when no bump flag specified).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files.")
        return parser

    @staticmethod
    def _resolve_bump_kind(options: argparse.Namespace) -> str:
        if options.major:
            return "major"
        if options.minor:
            return "minor"
        return "patch"

    @classmethod
    def run(cls, options: argparse.Namespace) -> int:
        current_version = cls.read_version_file(VERSION_FILE_PATH)
        pyproject_version = cls.read_pyproject_version(PYPROJECT_PATH)
        if current_version != pyproject_version:
            raise RuntimeError("Version mismatch between version.py and pyproject.toml.")

        current_parts = cls.parse_version(current_version)
        bump_kind = cls._resolve_bump_kind(options)

        if options.bump_ga:
            new_parts = cls.bump_ga(current_parts, bump_kind)
        else:
            if options.major or options.minor or options.patch:
                new_parts = cls.bump_hotfix(current_parts, bump_kind)
            else:
                new_parts = cls.bump_hotfix_build(current_parts)

        new_version = cls.format_version(new_parts)

        if options.dry_run:
            print(f"[dry-run] Current version: {current_version}")
            print(f"[dry-run] New version: {new_version}")
            print(f"[dry-run] Would run: {RELEASE_TEST_RUNNER}")
            print(f"[dry-run] Would commit and tag v{new_version}")
            print("[dry-run] Would push to origin.")
            return 0

        cls.ensure_git_clean()
        cls._run_release_tests()
        cls._cleanup_release_artifacts()
        cls.ensure_git_clean()

        cls.write_version_file(VERSION_FILE_PATH, new_version)
        cls.write_pyproject_version(PYPROJECT_PATH, new_version)
        print(f"Updated version to {new_version}")

        cls._commit_release(new_version)
        cls._tag_release(f"v{new_version}")
        cls._push_release(f"v{new_version}")

        return 0


def main() -> int:
    parser = ReleaseTool._build_parser()
    options = parser.parse_args()
    try:
        return ReleaseTool.run(options)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from getpass import getpass
from pathlib import Path

DIST_DIR = Path("dist")
PYPI_JSON_URL = "https://pypi.org/pypi/pypnm-docsis-cmts/json"
PYPI_UPLOAD_URL = "https://upload.pypi.org/legacy/"
PYPI_TOKEN_ENV = "PYPI_API_TOKEN"


class PublishTool:
    """Publish helper for PyPNM-CMTS package uploads."""

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Publish PyPNM-CMTS distributions to PyPI.")
        parser.add_argument(
            "--repository",
            choices=["pypi"],
            default="pypi",
            help="Target repository name for twine.",
        )
        parser.add_argument("--skip-build", action="store_true", help="Skip building distributions.")
        parser.add_argument("--skip-check", action="store_true", help="Skip twine check.")
        parser.add_argument("--dry-run", action="store_true", help="Skip twine upload.")
        parser.add_argument("--clean", action="store_true", help="Remove dist/ before building.")
        parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
        parser.add_argument("--force", action="store_true", help="Upload even if version exists on PyPI.")
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="Skip upload if version already exists on PyPI (default: true).",
        )
        return parser

    @staticmethod
    def _collect_artifacts() -> list[Path]:
        artifacts = sorted(path for path in DIST_DIR.glob("*") if path.is_file())
        if not artifacts:
            raise RuntimeError(f"No artifacts found in {DIST_DIR}.")
        return artifacts

    @staticmethod
    def _resolve_token() -> str:
        token = os.environ.get(PYPI_TOKEN_ENV, "").strip()
        if token != "":
            return token
        if not sys.stdin.isatty():
            raise RuntimeError("PYPI_API_TOKEN is required when stdin is not a TTY.")
        return getpass("PyPI token: ")

    @staticmethod
    def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
        subprocess.run(cmd, check=True, cwd=Path.cwd(), env=env)

    @staticmethod
    def _read_version() -> str:
        text = Path("pyproject.toml").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("version"):
                parts = line.split("=", maxsplit=1)
                if len(parts) == 2:
                    return parts[1].strip().strip("\"")
        raise RuntimeError("Unable to read version from pyproject.toml.")

    @classmethod
    def _version_exists(cls, version: str) -> bool:
        try:
            with urllib.request.urlopen(PYPI_JSON_URL) as response:
                data = json.load(response)
        except Exception as exc:
            print(f"WARNING: PyPI lookup failed ({exc}); continuing.", file=sys.stderr)
            return False
        releases = data.get("releases", {})
        return bool(releases.get(version))

    @staticmethod
    def _confirm_upload() -> bool:
        response = input("Proceed with upload to PyPI? [y/N]: ").strip().lower()
        return response in {"y", "yes"}

    @classmethod
    def run(cls, options: argparse.Namespace) -> int:
        if options.clean and DIST_DIR.exists():
            shutil.rmtree(DIST_DIR, ignore_errors=True)

        if not options.skip_build:
            cls._run([sys.executable, "-m", "build"])

        artifacts = cls._collect_artifacts()

        if not options.skip_check:
            check_cmd = [sys.executable, "-m", "twine", "check"]
            check_cmd.extend([str(path) for path in artifacts])
            cls._run(check_cmd)

        if options.dry_run:
            print("Dry-run enabled; skipping twine upload.")
            return 0

        publish_version = cls._read_version()
        version_exists = cls._version_exists(publish_version)
        if version_exists and bool(options.skip_existing) and not bool(options.force):
            print(f"Version {publish_version} already exists on PyPI; skipping upload.")
            return 0

        print(f"Publish version: {publish_version}")
        print(f"Artifacts: {len(artifacts)}")
        for artifact in artifacts:
            print(f"- {artifact.name}")
        print(f"Repository URL: {PYPI_UPLOAD_URL}")

        if not options.yes and not cls._confirm_upload():
            print("Upload cancelled.")
            return 0

        token = cls._resolve_token().strip()
        if token == "":
            raise RuntimeError("PyPI token is required for upload.")

        env = dict(os.environ)
        env["TWINE_USERNAME"] = "__token__"
        env["TWINE_PASSWORD"] = token

        upload_cmd = [sys.executable, "-m", "twine", "upload", "--repository", options.repository]
        upload_cmd.extend([str(path) for path in artifacts])
        cls._run(upload_cmd, env=env)
        return 0


def main() -> int:
    parser = PublishTool._build_parser()
    options = parser.parse_args()
    try:
        return PublishTool.run(options)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

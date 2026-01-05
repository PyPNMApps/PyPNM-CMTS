# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ScanFinding:
    path: str
    line_number: int
    message: str
    line: str


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    ignore_prefixes = (
        "tools/agent-review/",
        "tools/security/",
    )
    return [path for path in files if not path.startswith(ignore_prefixes)]


def _scan_file(path: str, patterns: list[tuple[re.Pattern[str], str]]) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                for pattern, message in patterns:
                    if pattern.search(line):
                        findings.append(
                            ScanFinding(
                                path=path,
                                line_number=idx,
                                message=message,
                                line=line.rstrip("\n"),
                            )
                        )
    except UnicodeDecodeError:
        return findings
    return findings


def _patterns() -> list[tuple[re.Pattern[str], str]]:
    return [
        (re.compile(r"retrival_method"), "Legacy config key: retrival_method"),
        (re.compile(r"AKIA[0-9A-Z]{16}"), "Potential AWS access key"),
        (re.compile(r"aws_secret_access_key", re.IGNORECASE), "Potential AWS secret key"),
        (re.compile(r"aws_access_key_id", re.IGNORECASE), "Potential AWS access key id"),
        (re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "Private key material"),
        (re.compile(r"xox[baprs]-[0-9A-Za-z-]+"), "Potential Slack token"),
        (re.compile(r"ghp_[0-9A-Za-z]{36}"), "Potential GitHub token"),
    ]


def main() -> int:
    patterns = _patterns()
    findings: list[ScanFinding] = []
    for path in _tracked_files():
        findings.extend(_scan_file(path, patterns))

    if not findings:
        print("legacy_key_scan: clean")
        return 0

    for finding in findings:
        print(f"{finding.path}:{finding.line_number}: {finding.message}: {finding.line}")
    print(f"legacy_key_scan: {len(findings)} findings")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

import pypnm

MIN_PYPNM_DOCSIS_VERSION = (1, 0, 18, 0)


def _parse_version(version: str) -> tuple[int, int, int, int]:
    parts = version.split(".")
    numbers: list[int] = []
    for part in parts[:4]:
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            numbers.append(int(digits))
        else:
            numbers.append(0)
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers)


def test_pypnm_docsis_version_present() -> None:
    """Ensure PyPNM-DOCSIS exposes a version string."""
    assert isinstance(pypnm.__version__, str)
    assert pypnm.__version__.strip()


def test_pypnm_docsis_version_minimum() -> None:
    """Ensure PyPNM-DOCSIS meets the minimum required version."""
    assert _parse_version(pypnm.__version__) >= MIN_PYPNM_DOCSIS_VERSION

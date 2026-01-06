# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.tools import release_tool


def test_parse_version_parts_valid() -> None:
    parts = release_tool._parse_version_parts("1.2.3.4")
    assert parts == [1, 2, 3, 4]


def test_parse_version_parts_invalid_count() -> None:
    with pytest.raises(SystemExit):
        release_tool._parse_version_parts("1.2.3")


def test_validate_version_string_non_numeric() -> None:
    with pytest.raises(SystemExit):
        release_tool._validate_version_string("1.2.x.4")


def test_compute_next_version_major() -> None:
    assert release_tool._compute_next_version("1.2.3.4", "major") == "2.0.0.0"


def test_compute_next_version_minor() -> None:
    assert release_tool._compute_next_version("1.2.3.4", "minor") == "1.3.0.0"


def test_compute_next_version_maintenance() -> None:
    assert release_tool._compute_next_version("1.2.3.4", "maintenance") == "1.2.4.0"


def test_compute_next_version_build() -> None:
    assert release_tool._compute_next_version("1.2.3.4", "build") == "1.2.3.5"


def test_determine_bump_kind() -> None:
    assert release_tool._determine_bump_kind("1.2.3.4", "2.0.0.0") == "major"
    assert release_tool._determine_bump_kind("1.2.3.4", "1.3.0.0") == "minor"
    assert release_tool._determine_bump_kind("1.2.3.4", "1.2.4.0") == "maintenance"
    assert release_tool._determine_bump_kind("1.2.3.4", "1.2.3.5") == "build"
    assert release_tool._determine_bump_kind("1.2.3.4", "1.2.3.4") == "none"

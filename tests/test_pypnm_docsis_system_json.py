# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from importlib import resources


def test_pypnm_docsis_system_json_accessible() -> None:
    """Ensure PyPNM-DOCSIS system.json is accessible and valid JSON."""
    system_json = resources.files("pypnm.settings").joinpath("system.json")
    assert system_json.is_file()

    with system_json.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert isinstance(data, dict)

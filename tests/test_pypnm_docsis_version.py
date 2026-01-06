# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pypnm


def test_pypnm_docsis_version_present() -> None:
    """Ensure PyPNM-DOCSIS exposes a version string."""
    assert isinstance(pypnm.__version__, str)
    assert pypnm.__version__.strip()

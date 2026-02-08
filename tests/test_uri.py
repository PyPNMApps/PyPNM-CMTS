# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import subprocess

import pytest

from pypnm_cmts.lib.types import UriStr
from pypnm_cmts.lib.uri import Uri


def test_uri_string_helpers() -> None:
    uri = Uri(UriStr("https://example.com:8443/path"))
    assert str(uri) == "https://example.com:8443/path"
    assert uri.to_string() == "https://example.com:8443/path"


def test_uri_invalid_format() -> None:
    with pytest.raises(ValueError):
        Uri(UriStr("example.com/path"))


def test_uri_resolve_model_live() -> None:
    uri = Uri(UriStr("https://example.com:8443/path"))
    resolved = uri.resolve()

    assert resolved.is_valid is True
    assert resolved.host == "example.com"
    assert resolved.port == 8443
    assert resolved.path == "/path"
    assert len(resolved.resolved_addresses) >= 1
    assert isinstance(resolved.is_pingable, bool)


def test_uri_not_pingable_on_ping_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _run(command: list[str], stdout: int, stderr: int, check: bool) -> subprocess.CompletedProcess[str]:
        raise OSError("ping not found")

    monkeypatch.setattr("pypnm_cmts.lib.uri.subprocess.run", _run)
    uri = Uri(UriStr("https://example.com"))
    assert uri.is_pingable() is False

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest
from pypnm.lib.types import HostNameStr

from pypnm_cmts.lib.cmts_hostname_resolver import resolve_cmts_inet


def test_resolve_cmts_inet_accepts_literal_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unexpected_resolve(self: object) -> list[str]:
        raise AssertionError("DNS should not run for literal IP input")

    monkeypatch.setattr("pypnm_cmts.lib.cmts_hostname_resolver.HostEndpoint.resolve", _unexpected_resolve)

    inet, resolved_ip = resolve_cmts_inet("192.168.0.10")
    assert str(inet) == "192.168.0.10"
    assert str(resolved_ip) == "192.168.0.10"


def test_resolve_cmts_inet_resolves_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    def _resolve(self: object) -> list[str]:
        return ["172.19.8.28"]

    monkeypatch.setattr("pypnm_cmts.lib.cmts_hostname_resolver.HostEndpoint.resolve", _resolve)

    inet, resolved_ip = resolve_cmts_inet(HostNameStr("cmts.example"))
    assert str(inet) == "172.19.8.28"
    assert str(resolved_ip) == "172.19.8.28"


def test_resolve_cmts_inet_raises_on_unresolvable_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    def _resolve(self: object) -> list[str]:
        return []

    monkeypatch.setattr("pypnm_cmts.lib.cmts_hostname_resolver.HostEndpoint.resolve", _resolve)

    with pytest.raises(ValueError, match="Failed to resolve hostname: cmts.example"):
        resolve_cmts_inet("cmts.example")


@pytest.mark.net
def test_resolve_cmts_inet_live_known_hostname() -> None:
    host = HostNameStr("www.google.com")
    try:
        inet, resolved_ip = resolve_cmts_inet(host)
    except ValueError as exc:
        pytest.skip(f"external DNS unavailable in this environment: {exc}")

    assert str(inet) == str(resolved_ip)
    assert str(resolved_ip).strip() != ""

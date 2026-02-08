# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet
from pypnm.lib.types import HostNameStr, InetAddressStr


def _parse_inet(value: str) -> Inet | None:
    try:
        return Inet(InetAddressStr(value))
    except ValueError:
        return None


def resolve_cmts_inet(hostname: HostNameStr | str) -> tuple[Inet, InetAddressStr]:
    """
    Resolve CMTS hostname or IP into a validated Inet and resolved IP string.

    Args:
        hostname (HostNameStr | str): CMTS hostname or literal IP address.

    Returns:
        tuple[Inet, InetAddressStr]: Validated Inet plus resolved IP string.

    Raises:
        ValueError: If the hostname is empty or cannot be resolved to a valid IP.
    """
    hostname_value = str(hostname).strip()
    if hostname_value == "":
        raise ValueError("CMTS hostname is required.")

    literal_inet = _parse_inet(hostname_value)
    if literal_inet is not None:
        return (literal_inet, InetAddressStr(str(literal_inet)))

    try:
        endpoint = HostEndpoint(HostNameStr(hostname_value))
        addresses = endpoint.resolve()
    except ValueError as exc:
        raise ValueError(f"Failed to resolve hostname: {hostname_value}") from exc

    for address in addresses:
        resolved_inet = _parse_inet(str(address))
        if resolved_inet is not None:
            return (resolved_inet, InetAddressStr(str(resolved_inet)))

    raise ValueError(f"Failed to resolve hostname: {hostname_value}")


__all__ = [
    "resolve_cmts_inet",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import socket
import subprocess
from urllib.parse import urlparse

from pydantic import BaseModel
from pypnm.lib.types import HostNameStr, InetAddressStr

from pypnm_cmts.lib.types import UriStr


class UriResolutionModel(BaseModel):
    """Resolved URI details."""

    uri: UriStr
    scheme: str
    host: HostNameStr
    port: int | None
    path: str
    resolved_addresses: list[InetAddressStr]
    is_pingable: bool
    is_valid: bool


class Uri:
    """URI wrapper with format validation, DNS resolution, and ping check."""

    def __init__(self, value: UriStr | str) -> None:
        uri_value = str(value).strip()
        self._uri = UriStr(uri_value)
        self._parsed = urlparse(uri_value)
        if not self.is_valid_format():
            raise ValueError(f"Invalid URI format: {uri_value}")

    def __str__(self) -> str:
        return str(self._uri)

    def to_string(self) -> str:
        return str(self._uri)

    @property
    def scheme(self) -> str:
        return self._parsed.scheme

    @property
    def host(self) -> HostNameStr:
        host = self._parsed.hostname
        if host is None:
            raise ValueError(f"Invalid URI host: {self._uri}")
        return HostNameStr(host)

    @property
    def port(self) -> int | None:
        return self._parsed.port

    @property
    def path(self) -> str:
        return self._parsed.path

    def is_valid_format(self) -> bool:
        if str(self._uri) == "":
            return False
        if self._parsed.scheme == "":
            return False
        return not (self._parsed.hostname is None or self._parsed.hostname.strip() == "")

    def get_resolved_addresses(self) -> list[InetAddressStr]:
        try:
            infos = socket.getaddrinfo(str(self.host), None)
        except (socket.gaierror, ValueError):
            return []
        resolved: list[InetAddressStr] = []
        for info in infos:
            address = info[4][0]
            inet = InetAddressStr(address)
            if inet not in resolved:
                resolved.append(inet)
        return resolved

    def is_pingable(self, timeout_seconds: int = 1) -> bool:
        host = str(self.host)
        command = ["ping", "-c", "1", "-W", str(timeout_seconds), host]
        try:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except OSError:
            return False
        return result.returncode == 0

    def resolve(self) -> UriResolutionModel:
        return UriResolutionModel(
            uri=self._uri,
            scheme=self.scheme,
            host=self.host,
            port=self.port,
            path=self.path,
            resolved_addresses=self.get_resolved_addresses(),
            is_pingable=self.is_pingable(),
            is_valid=self.is_valid_format(),
        )


__all__ = [
    "Uri",
    "UriResolutionModel",
]

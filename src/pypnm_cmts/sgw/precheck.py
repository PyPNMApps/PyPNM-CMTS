# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging

from pydantic import BaseModel, Field
from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet, InetAddressStr
from pypnm.lib.ping import Ping
from pypnm.lib.types import HostNameStr

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.docsis.cmts_operation import CmtsOperation


class CmtsStartupPrecheckResult(BaseModel):
    """Result of CMTS startup prechecks."""

    ping_ok: bool = Field(default=False, description="Whether ICMP ping succeeded.")
    snmp_ok: bool = Field(default=False, description="Whether SNMP sysDescr succeeded.")
    hostname: HostNameStr = Field(default=HostNameStr(""), description="CMTS hostname.")
    inet: InetAddressStr = Field(default=InetAddressStr(""), description="Resolved CMTS IP address.")
    error_message: str = Field(default="", description="Precheck failure message.")

    def is_ok(self) -> bool:
        """Return True when both ping and SNMP checks succeed."""
        return bool(self.ping_ok) and bool(self.snmp_ok) and self.error_message == ""


class CmtsStartupPrecheck:
    """Run CMTS reachability checks before SGW discovery."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    async def run(self, settings: CmtsOrchestratorSettings) -> CmtsStartupPrecheckResult:
        """
        Perform ping and SNMP reachability checks.
        """
        hostname_value = str(settings.adapter.hostname).strip()
        if hostname_value == "":
            return CmtsStartupPrecheckResult(error_message="adapter.hostname must be set for CMTS precheck")
        community_value = str(settings.adapter.community).strip()
        if community_value == "":
            return CmtsStartupPrecheckResult(error_message="adapter.community must be set for CMTS precheck")
        port_value = int(settings.adapter.port)

        inet = self._resolve_inet(hostname_value)
        if inet is None:
            return CmtsStartupPrecheckResult(
                hostname=HostNameStr(hostname_value),
                error_message="cmts hostname resolution failed",
            )

        inet_address = InetAddressStr(str(inet))
        ping_ok = self._ping_check(inet_address)
        snmp_ok = await self._snmp_check(inet, community_value, port_value)
        error_message = ""
        if not ping_ok:
            error_message = "cmts ping check failed"
        if ping_ok and not snmp_ok:
            error_message = "cmts snmp check failed"

        return CmtsStartupPrecheckResult(
            ping_ok=ping_ok,
            snmp_ok=snmp_ok,
            hostname=HostNameStr(hostname_value),
            inet=inet_address,
            error_message=error_message,
        )

    @staticmethod
    def _resolve_inet(hostname: str) -> Inet | None:
        endpoint = HostEndpoint(HostNameStr(hostname))
        addresses = endpoint.resolve()
        if not addresses:
            return None
        try:
            return Inet(addresses[0])
        except ValueError:
            return None

    @staticmethod
    def _ping_check(inet_address: InetAddressStr) -> bool:
        return bool(Ping.is_reachable(inet_address))

    async def _snmp_check(self, inet: Inet, community: str, port: int) -> bool:
        try:
            operation = CmtsOperation(inet=inet, write_community=community, port=port)
            sys_descr = await operation.getSysDescr()
        except Exception as exc:
            self.logger.error("SNMP precheck failed: %s", exc)
            return False
        return not sys_descr.is_empty


__all__ = [
    "CmtsStartupPrecheck",
    "CmtsStartupPrecheckResult",
]

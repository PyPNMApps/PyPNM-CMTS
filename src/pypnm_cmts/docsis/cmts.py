# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet, InetAddressStr
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.ping import Ping
from pypnm.lib.types import HostNameStr

from pypnm_cmts.docsis.cmts_operation import CmtsOperation


class Cmts(CmtsOperation):
    """
    Represents a CMTS device with SNMP operations and basic reachability checks.

    Provides access to CMTS identity metadata and utilities for ICMP and SNMP
    reachability testing.
    """

    inet: Inet

    def __init__(
        self,
        hostname: HostNameStr,
        inet: Inet,
        write_community: str = PnmConfigManager.get_write_community(),
    ) -> None:
        """
        Initialize the CMTS instance.

        Args:
            hostname (HostNameStr): Hostname or identifier for the CMTS.
            mac_address (MacAddress): The CMTS MAC address.
            inet (Inet): The IP address of the CMTS.
            write_community (str, optional): SNMP write community string. Defaults to the configured value.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        resolved_inet: Inet | None = None

        hostname_value: HostNameStr = hostname.strip()
        if hostname_value != "":
            endpoint = HostEndpoint(hostname_value)
            addresses = endpoint.resolve()
            if addresses:
                try:
                    resolved_inet = Inet(addresses[0])
                except ValueError as exc:
                    self.logger.warning(f"Invalid inet from hostname {hostname_value}: {exc}")
            else:
                self.logger.warning(f"Hostname resolution failed for {hostname_value}")

        inet_candidate: Inet | None = None
        if resolved_inet is None:
            if isinstance(inet, Inet):
                inet_candidate = inet
            else:
                self.logger.warning(f"Invalid inet provided: {type(inet).__name__}")

        if resolved_inet is None and inet_candidate is None:
            self.logger.error(f"Failed to resolve hostname or inet for {hostname_value}")
            exit(1)

        inet_to_use = resolved_inet if resolved_inet is not None else inet_candidate
        super().__init__(inet=inet_to_use, write_community=write_community)
        self._hostname: HostNameStr = hostname


    @property
    def get_hostname(self) -> HostNameStr:
        """
        Returns the hostname associated with the CMTS.

        Returns:
            HostNameStr: The CMTS hostname.
        """
        return self._hostname

    @property
    def get_inet_address(self) -> InetAddressStr:
        """
        Returns the IP address of the CMTS as a string.

        Returns:
            str: The CMTS IP address.
        """
        return InetAddressStr(self._inet.__str__())

    def is_ping_reachable(self) -> bool:
        """
        Checks whether the CMTS is reachable via ICMP ping.

        Returns:
            bool: True if the CMTS responds to ping, False otherwise.
        """
        return Ping.is_reachable(self.get_inet_address)

    async def is_snmp_reachable(self) -> bool:
        """
        Checks whether the CMTS is reachable via SNMP by requesting sysDescr.

        Returns:
            bool: True if SNMP communication is successful, False otherwise.
        """
        system_description = await self.getSysDescr()
        return not system_description.is_empty

    def same_inet_version(self, other: Inet) -> bool:
        """
        Determines whether this CMTS and another Inet address are the same IP version.

        Args:
            other (Inet): Another Inet instance to compare.

        Returns:
            bool: True if both are either IPv4 or IPv6, False otherwise.

        Raises:
            TypeError: If 'other' is not an instance of Inet.
        """
        if not isinstance(other, Inet):
            raise TypeError(f"Expected 'Inet' instance, got {type(other).__name__}")
        return self._inet.same_inet_version(other)

    def __str__(self) -> str:
        """
        String representation of the CMTS.

        Returns:
            str: Hostname and MAC address representation.
        """
        return f"{self.get_hostname} ({self.get_mac_address})"

    def __repr__(self) -> str:
        """
        String representation of the CMTS.

        Returns:
            str: Hostname, MAC, and IP address representation.
        """
        return f"Host: {self.get_hostname} - Mac: {self.get_mac_address} - Inet: {self.get_inet_address}"

    def __hash__(self) -> int:
        """
        Hash based on the normalized raw MAC address string (12 lowercase hex chars).

        This ensures that any MacAddress instance with the same underlying
        normalized MAC value will be treated as equal in sets and dicts.
        """
        return hash(self._mac_address.mac_address)

    def __eq__(self, other: object) -> bool:
        """
        Equality check based on the MAC address.
        """
        if isinstance(other, Cmts):
            return self._mac_address == other._mac_address
        if isinstance(other, MacAddress):
            return self._mac_address == other
        return False

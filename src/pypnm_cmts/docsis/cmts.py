# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.docsis.cm_snmp_operation import CmSnmpOperation
from pypnm.lib.inet import Inet, InetAddressStr
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import HostNameStr
from pypnm.lib.ping import Ping


class Cmts(CmSnmpOperation):
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
        super().__init__(inet=inet, write_community=write_community)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._hostname: HostNameStr = hostname
        self._mac_address: MacAddress = mac_address

    @property
    def get_hostname(self) -> HostNameStr:
        """
        Returns the hostname associated with the CMTS.

        Returns:
            HostNameStr: The CMTS hostname.
        """
        return self._hostname

    @property
    def get_mac_address(self) -> MacAddress:
        """
        Returns the MAC address of the CMTS.

        Returns:
            MacAddress: The CMTS MAC address.
        """
        return self._mac_address

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
        system_description = await self.getSysDescr(timeout=1, retries=1)
        return not system_description.is_empty()

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

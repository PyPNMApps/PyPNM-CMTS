# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.docsis.data_type.sysDescr import SystemDescriptor
from pypnm.lib.inet import Inet
from pypnm.snmp.snmp_v2c import Snmp_v2c


class CmtsOperation:
    """
    Minimal CMTS SNMP operation base class.

    Provides initialization and sysDescr lookup used by Cmts.
    """

    def __init__(self, inet: Inet, write_community: str, port: int = Snmp_v2c.SNMP_PORT) -> None:
        """
        Initialize the CMTS SNMP operation handler.

        Args:
            inet (Inet): CMTS IP address.
            write_community (str): SNMP write community string.
            port (int, optional): SNMP port. Defaults to Snmp_v2c.SNMP_PORT.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        if not isinstance(inet, Inet):
            self.logger.error(f"CmtsOperation() inet is of an Invalid Type: {type(inet)} , expecting Inet")
            exit(1)

        self._inet: Inet = inet
        self._community: str = write_community
        self._port: int = port
        self._snmp: Snmp_v2c = self.__load_snmp_version()

    def __load_snmp_version(self) -> Snmp_v2c:
        return Snmp_v2c(host=self._inet, community=self._community, port=self._port)

    async def getSysDescr(self) -> SystemDescriptor:
        """
        Fetch and parse sysDescr for the CMTS.

        Returns:
            SystemDescriptor: Parsed sysDescr or SystemDescriptor.empty() on failure.
        """
        try:
            result = await self._snmp.get(f'{"sysDescr"}.0')
        except Exception as exc:
            self.logger.error(f"SNMP get failed for sysDescr: {exc}")
            return SystemDescriptor.empty()

        if not result:
            return SystemDescriptor.empty()

        raw_value = Snmp_v2c.get_result_value(result)
        if not raw_value:
            return SystemDescriptor.empty()

        try:
            return SystemDescriptor.parse(raw_value)
        except ValueError as exc:
            self.logger.error(f"Failed to parse sysDescr: {exc}")
            return SystemDescriptor.empty()

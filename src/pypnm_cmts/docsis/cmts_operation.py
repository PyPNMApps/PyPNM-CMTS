# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.lib.inet import Inet
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class CmtsOperation:
    """
    Minimal CMTS SNMP operation base class.

    Provides initialization and sysDescr lookup used by Cmts.
    """

    def __init__(
        self,
        inet: Inet,
        write_community: str,
        port: int = Snmp_v2c.SNMP_PORT,
        snmp: Snmp_v2c | None = None,
    ) -> None:
        """
        Initialize the CMTS SNMP operation handler.

        Args:
            inet (Inet): CMTS IP address.
            write_community (str): SNMP write community string.
            port (int, optional): SNMP port. Defaults to Snmp_v2c.SNMP_PORT.
            snmp (Snmp_v2c | None, optional): Injected SNMP client for testing. Defaults to None.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        if not isinstance(inet, Inet):
            raise TypeError(
                f"CmtsOperation inet must be Inet, got {type(inet).__name__}"
            )

        self._inet: Inet = inet
        self._community: str = write_community
        self._port: int = port
        if snmp is None:
            self._snmp = self.__load_snmp_version()
        else:
            self._snmp = snmp

    def __load_snmp_version(self) -> Snmp_v2c:
        return Snmp_v2c(host=self._inet, community=self._community, port=self._port)

    async def getSysDescr(self) -> CmtsSysDescrModel:
        """
        Fetch and parse sysDescr for the CMTS.

        Returns:
            CmtsSysDescrModel: Parsed sysDescr or empty model on failure.
        """
        try:
            result = await self._snmp.get(f'{"sysDescr"}.0')
        except Exception as exc:
            self.logger.error(f"SNMP get failed for sysDescr: {exc}")
            return CmtsSysDescrModel.empty()

        if not result:
            return CmtsSysDescrModel.empty()

        raw_value = Snmp_v2c.get_result_value(result)
        if not raw_value:
            return CmtsSysDescrModel.empty()

        return CmtsSysDescrModel.parse(raw_value)

    async def get_sysdescr(self) -> CmtsSysDescrModel:
        """
        Fetch and parse sysDescr for the CMTS (snake_case alias).
        """
        return await self.getSysDescr()

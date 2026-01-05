# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet
from pypnm.lib.types import HostNameStr, InetAddressStr

from pypnm_cmts.api.routes.system.schemas import (
    CmtsSysDescrRequest,
    CmtsSysDescrResponse,
)
from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel

logger = logging.getLogger(__name__)


class SystemCmtsSnmpService:
    """
    Service class for CMTS system-level SNMP operations.
    """

    @staticmethod
    async def get_sysdescr(request: CmtsSysDescrRequest) -> CmtsSysDescrResponse:
        """
        Retrieve sysDescr for a CMTS using SNMP.
        """
        hostname_value = request.target.hostname
        if hostname_value == "":
            return CmtsSysDescrResponse(
                hostname=hostname_value,
                ip_address=InetAddressStr(""),
                status=ServiceStatusCode.FAILURE,
                message="CMTS hostname is required.",
                results=CmtsSysDescrModel.empty(),
            )

        resolved_ip = InetAddressStr("")
        inet: Inet
        try:
            inet = Inet(hostname_value)
            resolved_ip = InetAddressStr(hostname_value)
        except ValueError:
            resolved_ip = SystemCmtsSnmpService._resolve_hostname(hostname_value)
            if resolved_ip == "":
                return CmtsSysDescrResponse(
                    hostname=hostname_value,
                    ip_address=resolved_ip,
                    status=ServiceStatusCode.FAILURE,
                    message=f"Failed to resolve hostname: {hostname_value}",
                    results=CmtsSysDescrModel.empty(),
                )
            try:
                inet = Inet(resolved_ip)
            except ValueError as exc:
                return CmtsSysDescrResponse(
                    hostname=hostname_value,
                    ip_address=resolved_ip,
                    status=ServiceStatusCode.FAILURE,
                    message=f"Invalid CMTS IP address: {exc}",
                    results=CmtsSysDescrModel.empty(),
                )

        try:
            operation = CmtsOperation(
                inet=inet,
                write_community=request.snmp.snmp_v2c.community,
                port=request.snmp.port,
            )
            system_description = await operation.getSysDescr()
        except Exception as exc:
            logger.error(f"Failed to retrieve sysDescr: {exc}", exc_info=True)
            return CmtsSysDescrResponse(
                hostname=hostname_value,
                ip_address=resolved_ip,
                status=ServiceStatusCode.FAILURE,
                message=str(exc),
                results=CmtsSysDescrModel.empty(),
            )

        if system_description.is_empty:
            return CmtsSysDescrResponse(
                hostname=hostname_value,
                ip_address=resolved_ip,
                status=ServiceStatusCode.UNREACHABLE_SNMP,
                message="SNMP sysDescr returned empty.",
                results=system_description,
            )

        return CmtsSysDescrResponse(
            hostname=hostname_value,
            ip_address=resolved_ip,
            status=ServiceStatusCode.SUCCESS,
            message="",
            results=system_description,
        )

    @staticmethod
    def _resolve_hostname(hostname: HostNameStr) -> InetAddressStr:
        """
        Resolve a hostname to an IP address.
        """
        endpoint = HostEndpoint(hostname)
        addresses = endpoint.resolve()
        if not addresses:
            return InetAddressStr("")
        return InetAddressStr(addresses[0])

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import InetAddressStr

from pypnm_cmts.api.routes.system.schemas import (
    CmtsSysDescrRequest,
    CmtsSysDescrResponse,
)
from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel
from pypnm_cmts.lib.cmts_hostname_resolver import resolve_cmts_inet

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
        try:
            inet, resolved_ip = resolve_cmts_inet(hostname_value)
        except ValueError as exc:
            return CmtsSysDescrResponse(
                hostname=hostname_value,
                ip_address=resolved_ip,
                status=ServiceStatusCode.FAILURE,
                message=str(exc),
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

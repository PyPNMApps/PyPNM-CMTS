# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import HostNameStr, InetAddressStr

from pypnm_cmts.api.common.cmts.schema import CommonCmtsRequest
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class CmtsSysDescrRequest(CommonCmtsRequest):
    """
    Request model for CMTS sysDescr retrieval.
    """


class CmtsSysDescrResponse(BaseModel):
    """
    Response model for CMTS sysDescr retrieval.
    """
    hostname: HostNameStr = Field(default="", description="CMTS hostname or label.")
    ip_address: InetAddressStr = Field(default="", description="CMTS IP address.")
    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Result status code.")
    message: str = Field(default="", description="Informational or error message.")
    results: CmtsSysDescrModel = Field(default_factory=CmtsSysDescrModel.empty, description="Parsed CMTS sysDescr data.")


class CmtsWebServiceReloadResponse(BaseModel):
    """Response model for CMTS web-service reload requests."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Result status code.")
    message: str = Field(default="", description="Informational or error message.")
    reload_requested: bool = Field(default=True, description="True when the reload sentinel was written.")
    sentinel_path: str = Field(default="", description="Configured sentinel file path for the external watcher.")

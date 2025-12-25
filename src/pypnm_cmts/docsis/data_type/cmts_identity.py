# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.inet import InetAddressStr
from pypnm.lib.types import HostNameStr

from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class CmtsIdentityModel(BaseModel):
    hostname: HostNameStr           = Field(HostNameStr(""), description="CMTS hostname identifier.")
    inet: InetAddressStr            = Field(InetAddressStr(""), description="CMTS IP address.")
    sys_descr: CmtsSysDescrModel    = Field(default_factory=CmtsSysDescrModel.empty, description="Parsed sysDescr.")
    sys_name: str                   = Field("", description="SNMP sysName.")
    sys_object_id: str              = Field("", description="SNMP sysObjectID.")
    sys_uptime: int                 = Field(0, description="SNMP sysUpTime in timeticks.")
    is_empty: bool                  = Field(default=True, description="True when identity contains no SNMP information.")

    @classmethod
    def empty(
        cls,
        hostname: HostNameStr | None = None,
        inet: InetAddressStr | None = None,
    ) -> CmtsIdentityModel:
        if hostname is None:
            hostname = HostNameStr("")
        if inet is None:
            inet = InetAddressStr("")
        return cls(
            hostname        =   hostname,
            inet            =   inet,
            sys_descr       =   CmtsSysDescrModel.empty(),
            sys_name        =   "",
            sys_object_id   =   "",
            sys_uptime      =   0,
            is_empty        =   True,
        )

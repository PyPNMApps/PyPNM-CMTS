# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.types import InterfaceIndex

from pypnm_cmts.lib.types import MdCmSgId, MdDsSgId, MdUsSgId, NodeName


class CmtsServiceGroupModel(BaseModel):
    if_index: InterfaceIndex = Field(InterfaceIndex(0), description="MAC Domain ifIndex where the MD-CM-SG-ID is configured.")
    node_name: NodeName = Field(NodeName(""), description="Fiber node name associated with the MD-CM-SG.")
    md_cm_sg_id: MdCmSgId = Field(MdCmSgId(0), description="MD-CM-SG-ID (table index, parsed from OID).")
    md_ds_sg_id: MdDsSgId = Field(MdDsSgId(0), description="MD-DS-SG-ID value (walked from docsIf3MdNodeStatusMdDsSgId).")
    md_us_sg_id: MdUsSgId = Field(MdUsSgId(0), description="MD-US-SG-ID value (walked from docsIf3MdNodeStatusMdUsSgId).")


__all__ = [
    "CmtsServiceGroupModel",
]

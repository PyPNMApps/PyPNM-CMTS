# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.types import ChannelId, InterfaceIndex

from pypnm_cmts.lib.types import ChSetId, MdCmSgId, MdDsSgId, MdUsSgId, NodeName


class CmtsServiceGroupTopologyModel(BaseModel):
    """
    Service-group topology view.

    This model represents the join between:
        - MD node status service groups (nodeName, mdCmSgId, mdDsSgId/mdUsSgId)
        - DS/US ChSetId tables
        - DS/US channel-set channel lists
    """

    if_index : InterfaceIndex   = Field(..., description="ifIndex for the MAC Domain interface.")
    node_name: NodeName         = Field(..., description="MAC Domain node name.")
    md_cm_sg_id: MdCmSgId       = Field(..., description="MD CM Service Group ID from the OID index.")
    md_ds_sg_id: MdDsSgId       = Field(..., description="MD DS Service Group ID (walked value).")
    md_us_sg_id: MdUsSgId       = Field(..., description="MD US Service Group ID (walked value).")
    ds_exists: bool             = Field(..., description="True when DS ChSetId exists and was retrieved successfully.")
    us_exists: bool             = Field(..., description="True when US ChSetId exists and was retrieved successfully.")
    ds_ch_set_id: ChSetId       = Field(..., description="Downstream ChSetId for the service group.")
    us_ch_set_id: ChSetId       = Field(..., description="Upstream ChSetId for the service group.")
    ds_channels: list[ChannelId] = Field(..., description="Downstream channel list for ds_ch_set_id.")
    us_channels: list[ChannelId] = Field(..., description="Upstream channel list for us_ch_set_id.")


__all__ = [
    "CmtsServiceGroupTopologyModel",
]

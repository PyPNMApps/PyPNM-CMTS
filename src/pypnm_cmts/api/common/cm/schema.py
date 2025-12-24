from pydantic import BaseModel, Field
from pypnm.api.routes.common.classes.common_endpoint_classes.schema.base_snmp import (
    SNMPConfig,
)


class cmSnmpConfig(BaseModel):
    """
    SNMP configuration settings for CMTS requests.
    """
    snmp: SNMPConfig = Field(...,description="SNMP configuration block")

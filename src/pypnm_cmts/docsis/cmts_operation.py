# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from pypnm.lib.inet import Inet, InetAddressStr
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import ChannelId, HostNameStr, InterfaceIndex, MacAddressStr
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.data_type.cmts_cm_reg_status_entry import (
    DocsIf3CmtsCmRegStatusEntry,
    DocsIf3CmtsCmRegStatusIdEntry,
)
from pypnm_cmts.docsis.data_type.cmts_identity import CmtsIdentityModel
from pypnm_cmts.docsis.data_type.cmts_service_group import CmtsServiceGroupModel
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel
from pypnm_cmts.docsis.data_type.docs_if31_cmts_ds_ofdm_chan_entry import (
    DocsIf31CmtsDsOfdmChanRecord,
)
from pypnm_cmts.docsis.data_type.docs_if31_cmts_us_ofdma_chan_entry import (
    DocsIf31CmtsUsOfdmaChanRecord,
)
from pypnm_cmts.docsis.data_type.docs_if_downstream_channel_entry import (
    DocsIfDownstreamChannelEntry,
)
from pypnm_cmts.docsis.data_type.docs_if_upstream_channel_entry import (
    DocsIfUpstreamChannelEntry,
)
from pypnm_cmts.lib.types import (
    CableModemIndex,
    ChSetId,
    CmRegSgId,
    CmtsCmRegStatusId,
    CmtsCmRegStatusMacAddr,
    IPv4Str,
    IPv6LinkLocalStr,
    IPv6Str,
    MacAddressExist,
    MdCmSgId,
    MdDsSgId,
    MdNodeStatus,
    MdUsSgId,
    NodeName,
    RegisterCmInetAddress,
    RegisterCmMacInetAddress,
)

DEFAULT_MD_CM_SG_ID: MdCmSgId = MdCmSgId(0)
DEFAULT_CM_REG_SG_ID: CmRegSgId = CmRegSgId(0)
DEFAULT_MAC_ADDRESS_EXIST: MacAddressExist = MacAddressExist(False)
DEFAULT_CH_SET_ID: ChSetId = ChSetId(0)
EMPTY_REGISTER_CM_INET_ADDRESS: RegisterCmInetAddress = (
    IPv4Str(InetAddressStr('')),
    IPv6Str(InetAddressStr('')),
    IPv6LinkLocalStr(IPv6Str(InetAddressStr(''))),
)


@dataclass(frozen=True)
class _ServiceGroupKey:
    if_index: int
    node_name: str
    md_cm_sg_id: int


@dataclass(frozen=True)
class _ServiceGroupChSetKey:
    if_index: int
    sg_id: int


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
            raise TypeError(f"CmtsOperation inet must be Inet, got {type(inet).__name__}")

        self._inet: Inet = inet
        self._community: str = write_community
        self._port: int = port
        self._snmp = self.__load_snmp_version() if snmp is None else snmp

    def __load_snmp_version(self) -> Snmp_v2c:
        return Snmp_v2c(host=self._inet, community=self._community, port=self._port)

    @staticmethod
    def __oid0(oid: str) -> str:
        if oid.endswith(".0"):
            return oid
        return f"{oid}.0"

    @staticmethod
    def __get_result_value(result: object) -> str | None:
        if isinstance(result, list):
            if not result:
                return None
            return Snmp_v2c.get_result_value(result[0])
        return Snmp_v2c.get_result_value(result)  # type: ignore[arg-type]

    @staticmethod
    def __get_varbind_value(varbind: object) -> str | None:
        if isinstance(varbind, tuple) and len(varbind) >= 2:
            value = varbind[1]
            pretty = getattr(value, "prettyPrint", None)
            if callable(pretty):
                return pretty()
            if isinstance(value, (bytes, bytearray)):
                return value.decode("ascii", errors="ignore")
            return str(value)
        return Snmp_v2c.get_result_value(varbind)  # type: ignore[arg-type]

    async def __snmp_get_str(self, oid: str) -> str:
        oid0 = self.__oid0(oid)
        try:
            result = await self._snmp.get(oid0)
        except Exception as exc:
            self.logger.error(f"SNMP get failed for {oid0}: {exc}")
            return ""

        if not result:
            return ""

        raw_value = self.__get_result_value(result)
        if not raw_value:
            return ""

        return str(raw_value)

    async def __snmp_get_int(self, oid: str) -> int:
        raw_value = await self.__snmp_get_str(oid)
        if raw_value == "":
            return 0
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return 0

    async def getSysDescr(self) -> CmtsSysDescrModel:
        """
        Fetch and parse sysDescr for the CMTS.

        Returns:
            CmtsSysDescrModel: Parsed sysDescr or empty model on failure.
        """
        oid: str = "sysDescr"
        raw_value = await self.__snmp_get_str(oid)
        if raw_value == "":
            return CmtsSysDescrModel.empty()
        return CmtsSysDescrModel.parse(raw_value)

    async def getSysName(self) -> str:
        """
        Fetch sysName for the CMTS.

        Returns:
            str: sysName string.
        """
        oid: str = "sysName"
        return await self.__snmp_get_str(oid)

    async def getSysObjectId(self) -> str:
        """
        Fetch sysObjectID for the CMTS.

        Returns:
            str: sysObjectID string.
        """
        oid: str = "sysObjectID"
        return await self.__snmp_get_str(oid)

    async def getSysUpTime(self) -> int:
        """
        Fetch sysUpTime for the CMTS.

        Returns:
            int: sysUpTime in timeticks.
        """
        oid: str = "sysUpTime"
        return await self.__snmp_get_int(oid)

    async def getIdentity(self, hostname: HostNameStr = "") -> CmtsIdentityModel:
        """
        Fetch CMTS identity fields via SNMP.

        Returns:
            CmtsIdentityModel: CMTS identity model with empty/default values on failures.
        """
        sys_descr = await self.getSysDescr()
        sys_name = await self.getSysName()
        sys_object_id = await self.getSysObjectId()
        sys_uptime = await self.getSysUpTime()

        is_empty = (
            sys_descr.is_empty
            and sys_name == ""
            and sys_object_id == ""
            and sys_uptime == 0
        )

        return CmtsIdentityModel(
            hostname        =   hostname,
            inet            =   InetAddressStr(str(self._inet)),
            sys_descr       =   sys_descr,
            sys_name        =   sys_name,
            sys_object_id   =   sys_object_id,
            sys_uptime      =   sys_uptime,
            is_empty        =   is_empty,
        )

    async def getDocsIf3MdNodeStatusMdDsSgId(self) -> list[MdNodeStatus]:
        """
        Fetch DocsIf3MdNodeStatusMdDsSgId for all nodes.

        Returns:
            list[MdNodeStatus]: List of tuples containing InterfaceIndex, NodeName, MdCmSgId.
        """
        oid_base: str = "docsIf3MdNodeStatusMdDsSgId"
        return await self.__collect_md_node_status(oid_base)

    async def getDocsIf3MdNodeStatusMdUsSgId(self) -> list[MdNodeStatus]:
        """
        Fetch docsIf3MdNodeStatusMdUsSgId  for all nodes.

        Returns:
            list[MdNodeStatus]: List of tuples containing InterfaceIndex, NodeName, MdCmSgId.
        """
        oid_base: str = "docsIf3MdNodeStatusMdUsSgId"
        return await self.__collect_md_node_status(oid_base)

    async def getMdCmSgIdFromNodeName(
        self, node_name: NodeName | str
    ) -> tuple[bool, MdCmSgId]:
        """
        Fetch MD-CM-SG-ID for a matching node name.
        """
        if not isinstance(node_name, str) or isinstance(node_name, bool):
            raise TypeError(
                f"node_name must be NodeName or str, got {type(node_name).__name__}"
            )

        name_value = str(node_name).strip()
        if name_value == "":
            return (False, DEFAULT_MD_CM_SG_ID)

        try:
            ds_entries = await self.getDocsIf3MdNodeStatusMdDsSgId()
        except Exception as exc:
            self.logger.error(f"Failed to fetch DS node status: {exc}")
            ds_entries = []

        for _, entry_node, sg_id in ds_entries:
            if str(entry_node) == name_value:
                return (True, sg_id)

        try:
            us_entries = await self.getDocsIf3MdNodeStatusMdUsSgId()
        except Exception as exc:
            self.logger.error(f"Failed to fetch US node status: {exc}")
            return (False, DEFAULT_MD_CM_SG_ID)

        for _, entry_node, sg_id in us_entries:
            if str(entry_node) == name_value:
                return (True, sg_id)

        return (False, DEFAULT_MD_CM_SG_ID)

    async def getCmRegStatusSgIdFromNodeName(
        self, node_name: NodeName | str
    ) -> tuple[bool, CmRegSgId]:
        """
        Fetch CM registration SG ID from a node name.
        """
        if not isinstance(node_name, str) or isinstance(node_name, bool):
            raise TypeError(
                f"node_name must be NodeName or str, got {type(node_name).__name__}"
            )

        name_value = node_name.strip()
        if name_value == "":
            return (False, DEFAULT_CM_REG_SG_ID)

        oid_base: str = "docsIf3MdNodeStatusMdDsSgId"
        try:
            result = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return (False, DEFAULT_CM_REG_SG_ID)
        if not result:
            return (False, DEFAULT_CM_REG_SG_ID)

        limit = len(result)

        for idx in range(limit):
            parsed = self.__parse_md_node_status_oid_with_sg_id(oid_base, result[idx][0])
            if parsed is None:
                continue
            _, entry_node, cm_reg_sg_id = parsed
            if str(entry_node) == name_value:
                return (True, cm_reg_sg_id)

        return (False, DEFAULT_CM_REG_SG_ID)

    async def getCmRegStatusSgIdFromDsSgId(
        self, ds_sg_id: MdCmSgId | int
    ) -> tuple[bool, CmRegSgId]:
        """
        Fetch CM registration SG ID from a downstream SG ID value.
        """
        if not isinstance(ds_sg_id, int) or isinstance(ds_sg_id, bool):
            raise TypeError(
                f"ds_sg_id must be MdCmSgId or int, got {type(ds_sg_id).__name__}"
            )

        target = int(ds_sg_id)
        oid_base: str = "docsIf3MdNodeStatusMdDsSgId"
        try:
            result = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return (False, DEFAULT_CM_REG_SG_ID)
        if not result:
            return (False, DEFAULT_CM_REG_SG_ID)

        values = Snmp_v2c.snmp_get_result_value(result)
        if not values:
            return (False, DEFAULT_CM_REG_SG_ID)

        limit = len(result)
        if len(values) < limit:
            limit = len(values)

        for idx in range(limit):
            if not isinstance(values[idx], (int, str)):
                continue
            try:
                value_int = int(values[idx])
            except (TypeError, ValueError):
                continue
            if value_int != target:
                continue

            parsed = self.__parse_md_node_status_oid_with_sg_id(oid_base, result[idx][0])
            if parsed is None:
                continue
            return (True, parsed[2])

        return (False, DEFAULT_CM_REG_SG_ID)

    async def __collect_md_node_status(self, oid_base: str) -> list[MdNodeStatus]:
        """
        Collect node status entries from the provided OID base.
        """
        results: list[MdNodeStatus] = []
        try:
            result = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return results
        if not result:
            return results

        values = Snmp_v2c.snmp_get_result_value(result)

        if not values:
            return results

        limit = len(result)
        if len(values) < limit:
            limit = len(values)

        for idx in range(limit):
            parsed = self.__parse_md_node_status_oid(oid_base, result[idx][0])
            if parsed is None:
                continue
            interface_index, node_name = parsed
            try:
                sg_id_value = int(values[idx])
            except (TypeError, ValueError):
                continue

            results.append((interface_index, node_name, MdCmSgId(sg_id_value)))

        return results

    def __parse_md_node_status_oid(
        self, oid_base: str, oid_value: object
    ) -> tuple[InterfaceIndex, NodeName] | None:
        """
        Parse the OID suffix for docsIf3MdNodeStatus entries.
        """
        try:
            base_str = Snmp_v2c.resolve_oid(oid_base)
            base_tuple = tuple(int(part) for part in base_str.strip(".").split("."))
            oid_tuple = tuple(oid_value)
        except (TypeError, ValueError) as exc:
            self.logger.error(f"Failed to parse OID tuple for {oid_base}: {exc}")
            return None

        if len(oid_tuple) <= len(base_tuple) + 2:
            return None

        suffix = oid_tuple[len(base_tuple):]
        if len(suffix) < 3:
            return None

        interface_index = suffix[0]
        name_len = suffix[1]
        if not isinstance(interface_index, int) or not isinstance(name_len, int):
            return None

        if name_len < 0:
            return None

        if len(suffix) < 2 + name_len + 1:
            return None

        name_bytes = bytes(suffix[2:2 + name_len])
        try:
            node_name = NodeName(name_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            self.logger.error(f"Failed to decode node name for {oid_base}: {exc}")
            return None

        return (InterfaceIndex(int(interface_index)), node_name)

    def __parse_md_node_status_oid_with_sg_id(
        self, oid_base: str, oid_value: object
    ) -> tuple[InterfaceIndex, NodeName, CmRegSgId] | None:
        """
        Parse the OID suffix and return the CM registration SG ID.
        """
        try:
            base_str = Snmp_v2c.resolve_oid(oid_base)
            base_tuple = tuple(int(part) for part in base_str.strip(".").split("."))
            oid_tuple = tuple(oid_value)
        except (TypeError, ValueError) as exc:
            self.logger.error(f"Failed to parse OID tuple for {oid_base}: {exc}")
            return None

        if len(oid_tuple) <= len(base_tuple) + 2:
            return None

        suffix = oid_tuple[len(base_tuple):]
        if len(suffix) < 3:
            return None

        interface_index = suffix[0]
        name_len = suffix[1]
        if not isinstance(interface_index, int) or not isinstance(name_len, int):
            return None

        if name_len < 0:
            return None

        if len(suffix) < 2 + name_len + 1:
            return None

        name_bytes = bytes(suffix[2:2 + name_len])
        try:
            node_name = NodeName(name_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            self.logger.error(f"Failed to decode node name for {oid_base}: {exc}")
            return None

        cm_reg_sg_id = suffix[2 + name_len]
        if not isinstance(cm_reg_sg_id, int):
            return None

        return (InterfaceIndex(int(interface_index)), node_name, CmRegSgId(cm_reg_sg_id))

    def __parse_md_node_status_key(
        self, oid_base: str, oid_value: object
    ) -> MdNodeStatus | None:
        """
        Parse the OID suffix for docsIf3MdNodeStatus entries.

        Index:
            ifIndex,
            docsIf3MdNodeStatusNodeName (OCTET STRING),
            docsIf3MdNodeStatusMdCmSgId (Unsigned32)
        """
        try:
            base_str = Snmp_v2c.resolve_oid(oid_base)
            base_tuple = tuple(int(part) for part in base_str.strip(".").split("."))
            oid_tuple = tuple(oid_value)
        except (TypeError, ValueError) as exc:
            self.logger.error(f"Failed to parse OID tuple for {oid_base}: {exc}")
            return None

        if len(oid_tuple) <= len(base_tuple) + 2:
            return None

        suffix = oid_tuple[len(base_tuple):]
        if len(suffix) < 4:
            return None

        interface_index = suffix[0]
        name_len = suffix[1]
        if not isinstance(interface_index, int) or not isinstance(name_len, int):
            return None

        if name_len < 0:
            return None

        name_end = 2 + name_len
        if len(suffix) <= name_end:
            return None

        name_bytes = bytes(suffix[2:name_end])
        try:
            node_name = NodeName(name_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            self.logger.error(f"Failed to decode node name for {oid_base}: {exc}")
            return None

        md_cm_sg_id_raw = suffix[name_end]
        if not isinstance(md_cm_sg_id_raw, int):
            return None

        return (
            InterfaceIndex(int(interface_index)),
            node_name,
            MdCmSgId(int(md_cm_sg_id_raw)),
        )

    async def __collect_md_node_status_value(
        self, oid_base: str
    ) -> list[tuple[MdNodeStatus, int]]:
        """
        Collect MD node status (key, value) for the provided OID base.

        The value is the walked column value (MD-DS-SG-ID or MD-US-SG-ID).
        """
        results: list[tuple[MdNodeStatus, int]] = []
        try:
            walk_results = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return results

        if not walk_results:
            return results

        values = Snmp_v2c.snmp_get_result_value(walk_results)
        if not values:
            return results

        limit = len(walk_results)
        if len(values) < limit:
            limit = len(values)

        for idx in range(limit):
            parsed_key = self.__parse_md_node_status_key(oid_base, walk_results[idx][0])
            if parsed_key is None:
                continue
            if not isinstance(values[idx], (int, str)):
                continue
            try:
                col_value = int(values[idx])
            except (TypeError, ValueError):
                continue
            results.append((parsed_key, col_value))

        return results

    async def listServiceGroups(self) -> list[CmtsServiceGroupModel]:
        """
        Enumerate service groups using DOCS-IF3 MD Node Status.

        Data model:
            - Key (from OID index): ifIndex, nodeName, mdCmSgId
            - Values (walked):
                docsIf3MdNodeStatusMdDsSgId -> mdDsSgId
                docsIf3MdNodeStatusMdUsSgId -> mdUsSgId
        """
        ds_oid = "docsIf3MdNodeStatusMdDsSgId"
        us_oid = "docsIf3MdNodeStatusMdUsSgId"

        merged: dict[_ServiceGroupKey, CmtsServiceGroupModel] = {}

        ds_rows = await self.__collect_md_node_status_value(ds_oid)
        for key, ds_value in ds_rows:
            if_index, node_name, md_cm_sg_id = key
            dict_key = _ServiceGroupKey(
                int(if_index),
                str(node_name),
                int(md_cm_sg_id),
            )
            merged[dict_key] = CmtsServiceGroupModel(
                if_index    =   if_index,
                node_name   =   node_name,
                md_cm_sg_id =   md_cm_sg_id,
                md_ds_sg_id =   MdDsSgId(ds_value),
                md_us_sg_id =   MdUsSgId(0),
            )

        us_rows = await self.__collect_md_node_status_value(us_oid)
        for key, us_value in us_rows:
            if_index, node_name, md_cm_sg_id = key
            dict_key = _ServiceGroupKey(
                int(if_index),
                str(node_name),
                int(md_cm_sg_id),
            )
            if dict_key not in merged:
                merged[dict_key] = CmtsServiceGroupModel(
                    if_index    =   if_index,
                    node_name   =   node_name,
                    md_cm_sg_id =   md_cm_sg_id,
                    md_ds_sg_id =   MdDsSgId(0),
                    md_us_sg_id =   MdUsSgId(us_value),
                )
            else:
                merged[dict_key].md_us_sg_id = MdUsSgId(us_value)

        sorted_keys = sorted(
            merged.keys(),
            key=lambda key: (key.if_index, key.node_name, key.md_cm_sg_id),
        )
        return [merged[k] for k in sorted_keys]

    @staticmethod
    def __parse_channel_list(raw_value: str) -> list[ChannelId]:
        text = raw_value
        if isinstance(raw_value, (bytes, bytearray)):
            text = raw_value.decode("ascii", errors="ignore")
        else:
            text = str(raw_value)

        if text.startswith("0x"):
            hex_str = text[2:]
            if len(hex_str) % 2 == 0:
                try:
                    raw_bytes = bytes.fromhex(hex_str)
                    return [ChannelId(byte) for byte in raw_bytes]
                except ValueError:
                    pass

        numbers = re.findall(r"\d+", text)
        return [ChannelId(int(value)) for value in numbers]

    async def __collect_ch_set_id_map(
        self, oid_base: str
    ) -> dict[_ServiceGroupChSetKey, ChSetId]:
        ch_set_map: dict[_ServiceGroupChSetKey, ChSetId] = {}
        try:
            walk_results = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return ch_set_map

        if not walk_results:
            return ch_set_map

        base_str = Snmp_v2c.resolve_oid(oid_base)
        base_prefix = f"{base_str}."
        for idx in range(len(walk_results)):
            oid_value = walk_results[idx][0]
            oid_str = str(oid_value).lstrip(".")
            if not oid_str.startswith(base_prefix):
                continue

            suffix_str = oid_str[len(base_prefix):]
            parts = suffix_str.split(".")
            if len(parts) < 2:
                continue

            try:
                if_index = int(parts[0])
                sg_id = int(parts[1])
            except (TypeError, ValueError):
                continue

            try:
                raw_value = self.__get_varbind_value(walk_results[idx])
                if raw_value is None:
                    continue
                ch_set_id = int(str(raw_value))
            except (TypeError, ValueError):
                continue

            ch_set_map[_ServiceGroupChSetKey(int(if_index), int(sg_id))] = ChSetId(
                ch_set_id
            )

        return ch_set_map

    async def __collect_channel_list_map(
        self, oid_base: str
    ) -> dict[_ServiceGroupChSetKey, list[ChannelId]]:
        channel_map: dict[_ServiceGroupChSetKey, list[ChannelId]] = {}
        try:
            walk_results = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return channel_map

        if not walk_results:
            return channel_map

        base_str = Snmp_v2c.resolve_oid(oid_base)
        base_prefix = f"{base_str}."
        for idx in range(len(walk_results)):
            oid_value = walk_results[idx][0]
            oid_str = str(oid_value).lstrip(".")
            if not oid_str.startswith(base_prefix):
                continue

            suffix_str = oid_str[len(base_prefix):]
            parts = suffix_str.split(".")
            if len(parts) < 2:
                continue

            try:
                if_index = int(parts[0])
                ch_set_id = int(parts[1])
            except (TypeError, ValueError):
                continue

            raw_value = self.__get_varbind_value(walk_results[idx])
            if raw_value is None:
                continue

            channels = self.__parse_channel_list(str(raw_value))

            channel_map[_ServiceGroupChSetKey(int(if_index), int(ch_set_id))] = channels

        return channel_map

    async def getDocsIf3MdDsSgStatusChSetId(
        self,
        if_index: InterfaceIndex,
        md_ds_sg_id: MdDsSgId,
    ) -> tuple[bool, ChSetId]:
        """
        Fetch ChSetId for a MAC Domain downstream service group.

        OID:
            docsIf3MdDsSgStatusChSetId

        Index:
            ifIndex,
            docsIf3MdDsSgStatusMdDsSgId
        """
        if not isinstance(if_index, int) or isinstance(if_index, bool):
            raise TypeError(
                f"if_index must be InterfaceIndex, got {type(if_index).__name__}"
            )
        if not isinstance(md_ds_sg_id, int) or isinstance(md_ds_sg_id, bool):
            raise TypeError(
                f"md_ds_sg_id must be MdDsSgId, got {type(md_ds_sg_id).__name__}"
            )

        oid_base: str = "docsIf3MdDsSgStatusChSetId"
        oid = f"{oid_base}.{int(if_index)}.{int(md_ds_sg_id)}"

        try:
            result = await self._snmp.get(oid)
        except Exception as exc:
            self.logger.error(f"SNMP get failed for {oid}: {exc}")
            return (False, DEFAULT_CH_SET_ID)
        if not result:
            return (False, DEFAULT_CH_SET_ID)

        raw_value = Snmp_v2c.get_result_value(result)
        if raw_value is None:
            return (False, DEFAULT_CH_SET_ID)

        try:
            ch_set_id = int(str(raw_value))
        except (TypeError, ValueError):
            return (False, DEFAULT_CH_SET_ID)

        return (True, ChSetId(ch_set_id))

    async def getDocsIf3MdUsSgStatusChSetId(
        self,
        if_index: InterfaceIndex,
        md_us_sg_id: MdUsSgId,
    ) -> tuple[bool, ChSetId]:
        """
        Fetch ChSetId for a MAC Domain upstream service group.

        OID:
            docsIf3MdUsSgStatusChSetId

        Index:
            ifIndex,
            docsIf3MdUsSgStatusMdUsSgId
        """
        if not isinstance(if_index, int) or isinstance(if_index, bool):
            raise TypeError(
                f"if_index must be InterfaceIndex, got {type(if_index).__name__}"
            )
        if not isinstance(md_us_sg_id, int) or isinstance(md_us_sg_id, bool):
            raise TypeError(
                f"md_us_sg_id must be MdUsSgId, got {type(md_us_sg_id).__name__}"
            )

        oid_base: str = "docsIf3MdUsSgStatusChSetId"
        oid = f"{oid_base}.{int(if_index)}.{int(md_us_sg_id)}"

        try:
            result = await self._snmp.get(oid)
        except Exception as exc:
            self.logger.error(f"SNMP get failed for {oid}: {exc}")
            return (False, DEFAULT_CH_SET_ID)
        if not result:
            return (False, DEFAULT_CH_SET_ID)

        raw_value = Snmp_v2c.get_result_value(result)
        if raw_value is None:
            return (False, DEFAULT_CH_SET_ID)

        try:
            ch_set_id = int(str(raw_value))
        except (TypeError, ValueError):
            return (False, DEFAULT_CH_SET_ID)

        return (True, ChSetId(ch_set_id))

    async def getDocsIf3DsChSetChList(
        self,
        if_index: InterfaceIndex,
        ch_set_id: ChSetId,
    ) -> list[ChannelId]:
        """
        Fetch downstream channel list for a given ChSetId.

        OID:
            docsIf3DsChSetChList

        Index:
            docsIf3DsChSetId
        """
        if not isinstance(if_index, int) or isinstance(if_index, bool):
            raise TypeError(
                f"if_index must be InterfaceIndex, got {type(if_index).__name__}"
            )
        if not isinstance(ch_set_id, int) or isinstance(ch_set_id, bool):
            raise TypeError(
                f"ch_set_id must be ChSetId, got {type(ch_set_id).__name__}"
            )

        oid_base: str = "docsIf3DsChSetChList"
        oid = f"{oid_base}.{int(if_index)}.{int(ch_set_id)}"

        try:
            result = await self._snmp.get(oid)
        except Exception as exc:
            self.logger.error(f"SNMP get failed for {oid}: {exc}")
            result = None
        if result:
            raw_value = self.__get_result_value(result)
            if raw_value is not None:
                return self.__parse_channel_list(str(raw_value))

        channel_map = await self.__collect_channel_list_map(oid_base)
        channel_key = _ServiceGroupChSetKey(int(if_index), int(ch_set_id))
        return channel_map.get(channel_key, [])

    async def getDocsIf3UsChSetChList(
        self,
        if_index: InterfaceIndex,
        ch_set_id: ChSetId,
    ) -> list[ChannelId]:
        """
        Fetch upstream channel list for a given ChSetId.

        OID:
            docsIf3UsChSetChList

        Index:
            docsIf3UsChSetId
        """
        if not isinstance(if_index, int) or isinstance(if_index, bool):
            raise TypeError(
                f"if_index must be InterfaceIndex, got {type(if_index).__name__}"
            )
        if not isinstance(ch_set_id, int) or isinstance(ch_set_id, bool):
            raise TypeError(
                f"ch_set_id must be ChSetId, got {type(ch_set_id).__name__}"
            )

        oid_base: str = "docsIf3UsChSetChList"
        oid = f"{oid_base}.{int(if_index)}.{int(ch_set_id)}"

        try:
            result = await self._snmp.get(oid)
        except Exception as exc:
            self.logger.error(f"SNMP get failed for {oid}: {exc}")
            result = None
        if result:
            raw_value = self.__get_result_value(result)
            if raw_value is not None:
                return self.__parse_channel_list(str(raw_value))

        channel_map = await self.__collect_channel_list_map(oid_base)
        channel_key = _ServiceGroupChSetKey(int(if_index), int(ch_set_id))
        return channel_map.get(channel_key, [])

    async def getServiceGroupTopology(self) -> list[CmtsServiceGroupTopologyModel]:
        """
        Build a service-group topology view by joining:

        Inputs:
            listServiceGroups()

        Joins:
            docsIf3MdDsSgStatusChSetId   -> DS ChSetId
            docsIf3MdUsSgStatusChSetId   -> US ChSetId
            docsIf3DsChSetChList         -> DS channel list
            docsIf3UsChSetChList         -> US channel list
        """
        results: list[CmtsServiceGroupTopologyModel] = []
        service_groups = await self.listServiceGroups()
        ds_ch_set_map = await self.__collect_ch_set_id_map(
            "docsIf3MdDsSgStatusChSetId"
        )
        us_ch_set_map = await self.__collect_ch_set_id_map(
            "docsIf3MdUsSgStatusChSetId"
        )
        ds_channel_map = await self.__collect_channel_list_map("docsIf3DsChSetChList")
        us_channel_map = await self.__collect_channel_list_map("docsIf3UsChSetChList")

        for group in service_groups:
            ds_exists: bool = False
            ds_ch_set_id: ChSetId = DEFAULT_CH_SET_ID
            if int(group.md_ds_sg_id) > 0:
                ds_key = _ServiceGroupChSetKey(
                    int(group.if_index),
                    int(group.md_ds_sg_id),
                )
                if ds_ch_set_map:
                    if ds_key in ds_ch_set_map:
                        ds_exists = True
                        ds_ch_set_id = ds_ch_set_map[ds_key]
                else:
                    ds_exists, ds_ch_set_id = await self.getDocsIf3MdDsSgStatusChSetId(
                        group.if_index,
                        group.md_ds_sg_id,
                    )

            us_exists: bool = False
            us_ch_set_id: ChSetId = DEFAULT_CH_SET_ID
            if int(group.md_us_sg_id) > 0:
                us_key = _ServiceGroupChSetKey(
                    int(group.if_index),
                    int(group.md_us_sg_id),
                )
                if us_ch_set_map:
                    if us_key in us_ch_set_map:
                        us_exists = True
                        us_ch_set_id = us_ch_set_map[us_key]
                else:
                    us_exists, us_ch_set_id = await self.getDocsIf3MdUsSgStatusChSetId(
                        group.if_index,
                        group.md_us_sg_id,
                    )

            ds_channels: list[ChannelId] = []
            ds_channel_key = _ServiceGroupChSetKey(
                int(group.if_index),
                int(ds_ch_set_id),
            )
            if ds_channel_key in ds_channel_map:
                ds_channels = ds_channel_map[ds_channel_key]
            else:
                if bool(ds_exists) and int(ds_ch_set_id) > 0:
                    ds_channels = await self.getDocsIf3DsChSetChList(
                        group.if_index,
                        ds_ch_set_id,
                    )

            us_channels: list[ChannelId] = []
            us_channel_key = _ServiceGroupChSetKey(
                int(group.if_index),
                int(us_ch_set_id),
            )
            if us_channel_key in us_channel_map:
                us_channels = us_channel_map[us_channel_key]
            else:
                if bool(us_exists) and int(us_ch_set_id) > 0:
                    us_channels = await self.getDocsIf3UsChSetChList(
                        group.if_index,
                        us_ch_set_id,
                    )

            results.append(
                CmtsServiceGroupTopologyModel(
                    if_index        =   group.if_index,
                    node_name       =   group.node_name,
                    md_cm_sg_id     =   group.md_cm_sg_id,
                    md_ds_sg_id     =   group.md_ds_sg_id,
                    md_us_sg_id     =   group.md_us_sg_id,
                    ds_exists       =   bool(ds_exists),
                    us_exists       =   bool(us_exists),
                    ds_ch_set_id    =   ds_ch_set_id,
                    us_ch_set_id    =   us_ch_set_id,
                    ds_channels     =   ds_channels,
                    us_channels     =   us_channels,
                )
            )

        return results

    async def getDocsIfDownstreamChannelEntry(self) -> list[DocsIfDownstreamChannelEntry]:
        """
        Fetch DOCS-IF downstream channel table entries.
        """
        try:
            return await DocsIfDownstreamChannelEntry.get_all(self._snmp)
        except Exception as exc:
            self.logger.error(f"Failed to retrieve downstream channel entries: {exc}")
            return []

    async def getDocsIfUpstreamChannelEntry(self) -> list[DocsIfUpstreamChannelEntry]:
        """
        Fetch DOCS-IF upstream channel table entries.
        """
        try:
            return await DocsIfUpstreamChannelEntry.get_all(self._snmp)
        except Exception as exc:
            self.logger.error(f"Failed to retrieve upstream channel entries: {exc}")
            return []

    async def getDocsIf31CmtsDsOfdmChanEntry(self) -> list[DocsIf31CmtsDsOfdmChanRecord]:
        """
        Fetch DOCS-IF31 downstream OFDM channel entries.
        """
        try:
            return await DocsIf31CmtsDsOfdmChanRecord.get_all(self._snmp)
        except Exception as exc:
            self.logger.error(f"Failed to retrieve downstream OFDM channel entries: {exc}")
            return []

    async def getDocsIf31CmtsUsOfdmaChanEntry(self) -> list[DocsIf31CmtsUsOfdmaChanRecord]:
        """
        Fetch DOCS-IF31 upstream OFDMA channel entries.
        """
        try:
            return await DocsIf31CmtsUsOfdmaChanRecord.get_all(self._snmp)
        except Exception as exc:
            self.logger.error(f"Failed to retrieve upstream OFDMA channel entries: {exc}")
            return []

    async def getdocsIf3CmtsCmRegStatusMdCmSgIdViaMacAddress(self, mac: MacAddress) -> tuple[MacAddressExist, MdCmSgId]:
        """
        Fetch docsIf3CmtsCmRegStatusMdCmSgId for a matching MAC address.

        Returns:
           tuple[MacAddressExist, MdCmSgId]: Tuple indicating if MAC exists and the MdCmSgId value.
        """
        if not isinstance(mac, MacAddress):
            raise TypeError(f"mac must be MacAddress, got {type(mac).__name__}")
        mac_oid: str = "docsIf3CmtsCmRegStatusMacAddr"
        try:
            mac_results = await self._snmp.walk(mac_oid)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {mac_oid}: {exc}")
            return (DEFAULT_MAC_ADDRESS_EXIST, DEFAULT_MD_CM_SG_ID)
        if not mac_results:
            return (DEFAULT_MAC_ADDRESS_EXIST, DEFAULT_MD_CM_SG_ID)

        mac_indices = Snmp_v2c.extract_last_oid_index(mac_results)
        mac_values = Snmp_v2c.snmp_get_result_bytes(mac_results)
        if not mac_indices or not mac_values:
            return (DEFAULT_MAC_ADDRESS_EXIST, DEFAULT_MD_CM_SG_ID)

        found_index: int | None = None
        limit = len(mac_indices)
        if len(mac_values) < limit:
            limit = len(mac_values)

        for idx in range(limit):
            if not isinstance(mac_values[idx], (bytes, str)):
                continue
            try:
                candidate = MacAddress(mac_values[idx])
            except (TypeError, ValueError):
                continue
            if candidate.is_equal(mac):
                found_index = int(mac_indices[idx])
                break

        if found_index is None:
            return (DEFAULT_MAC_ADDRESS_EXIST, DEFAULT_MD_CM_SG_ID)

        sg_oid: str = "docsIf3CmtsCmRegStatusMdCmSgId"
        try:
            sg_results = await self._snmp.walk(sg_oid)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {sg_oid}: {exc}")
            return (MacAddressExist(True), DEFAULT_MD_CM_SG_ID)
        if not sg_results:
            return (MacAddressExist(True), DEFAULT_MD_CM_SG_ID)

        sg_indices = Snmp_v2c.extract_last_oid_index(sg_results)
        sg_values = Snmp_v2c.snmp_get_result_value(sg_results)
        if not sg_indices or not sg_values:
            return (MacAddressExist(True), DEFAULT_MD_CM_SG_ID)

        sg_limit = len(sg_indices)
        if len(sg_values) < sg_limit:
            sg_limit = len(sg_values)

        for idx in range(sg_limit):
            if not isinstance(sg_indices[idx], (int, str)):
                continue
            try:
                index_int = int(sg_indices[idx])
            except (TypeError, ValueError):
                continue
            if index_int != found_index:
                continue

            if not isinstance(sg_values[idx], (int, str)):
                return (MacAddressExist(True), DEFAULT_MD_CM_SG_ID)
            try:
                sg_id_value = int(sg_values[idx])
            except (TypeError, ValueError):
                return (MacAddressExist(True), DEFAULT_MD_CM_SG_ID)

            return (MacAddressExist(True), MdCmSgId(sg_id_value))

        return (MacAddressExist(True), DEFAULT_MD_CM_SG_ID)

    async def getDocsIf3CmtsCmRegStatusMacAddr(self) -> list[CmtsCmRegStatusMacAddr]:
        """
        Fetch docsIf3CmtsCmRegStatusMacAddr for all nodes.

        Returns:
            list[CmtsCmRegStatusMacAddr]: List of tuples containing CmtsCmRegStatusId, MacAddressStr.
        """
        indices: list[int]
        results: list[CmtsCmRegStatusMacAddr] = []
        oid_base: str = "docsIf3CmtsCmRegStatusMacAddr"
        try:
            result = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return results
        if not result:
            return results

        indices = Snmp_v2c.extract_last_oid_index(result)
        values = Snmp_v2c.snmp_get_result_bytes(result)

        if not indices or not values:
            return results

        limit = len(indices)
        if len(values) < limit:
            limit = len(values)

        for idx in range(limit):
            if not isinstance(indices[idx], (int, str)):
                continue
            try:
                reg_status_id = CmtsCmRegStatusId(int(indices[idx]))
            except (TypeError, ValueError):
                continue

            if not isinstance(values[idx], (bytes, str)):
                continue
            try:
                mac_value = MacAddress(values[idx])
            except (TypeError, ValueError):
                continue

            results.append((reg_status_id, MacAddressStr(str(mac_value))))

        return results

    async def getAllRegisterCm(self, serving_group_id: MdCmSgId) -> list[DocsIf3CmtsCmRegStatusEntry]:
        """
        Fetch all registered CM entries for a given serving group ID.

        Args:
            serving_group_id (MdCmSgId): The serving group ID to filter by.
        Returns:
            list[DocsIf3CmtsCmRegStatusEntry]: List of registered CM entries for the given serving group ID.
        """
        if not isinstance(serving_group_id, int) or isinstance(serving_group_id, bool):
            raise TypeError(
                f"serving_group_id must be MdCmSgId, got {type(serving_group_id).__name__}"
            )

        results: list[DocsIf3CmtsCmRegStatusEntry] = []
        oid_base: str = "docsIf3CmtsCmRegStatusMdCmSgId"
        try:
            sg_results = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return results
        if not sg_results:
            return results

        indices = Snmp_v2c.extract_last_oid_index(sg_results)
        values = Snmp_v2c.snmp_get_result_value(sg_results)
        if not indices or not values:
            return results

        target = int(serving_group_id)
        matched_indices: list[int] = []
        limit = len(indices)
        if len(values) < limit:
            limit = len(values)

        for idx in range(limit):
            if not isinstance(values[idx], (int, str)):
                continue
            try:
                value_int = int(values[idx])
            except (TypeError, ValueError):
                continue
            if value_int != target:
                continue
            matched_indices.append(int(indices[idx]))

        if not matched_indices:
            return results

        try:
            results = await DocsIf3CmtsCmRegStatusIdEntry.get_entries(
                self._snmp, matched_indices
            )
        except Exception as exc:
            self.logger.error(f"Failed to fetch CM registration entries: {exc}")
            return []

        return results

    async def getAllRegisterCmMacInetAddress(
        self, serving_group_id: MdCmSgId
    ) -> list[RegisterCmMacInetAddress]:
        """
        Fetch all registered CM entries for a given serving group ID.

        Args:
            serving_group_id (MdCmSgId): The serving group ID to filter by.
        Returns:
            list[RegisterCmMacInetAddress]: Tuples containing CableModemIndex, MacAddressStr, IPv4Str, IPv6Str, IPv6LinkLocalStr.

        DOCS-IF3-MIB::docsIf3CmtsCmRegStatusMacAddr.786433 = STRING: fc:77:7b:cc:4:20
        DOCS-IF3-MIB::docsIf3CmtsCmRegStatusIPv6Addr.786433 = STRING: 0:0:0:0:0:0:0:0
        DOCS-IF3-MIB::docsIf3CmtsCmRegStatusIPv6LinkLocal.786433 = STRING: 0:0:0:0:0:0:0:0
        DOCS-IF3-MIB::docsIf3CmtsCmRegStatusIPv4Addr.786433 = STRING: 172.19.16.247

        Do not use getAllRegisterCm(), this should be faster, you need only 4 gets.
        """
        if not isinstance(serving_group_id, int) or isinstance(serving_group_id, bool):
            raise TypeError(
                f"serving_group_id must be MdCmSgId, got {type(serving_group_id).__name__}"
            )

        results: list[RegisterCmMacInetAddress] = []
        oid_base: str = "docsIf3CmtsCmRegStatusMdCmSgId"
        try:
            sg_results = await self._snmp.walk(oid_base)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
            return results
        if not sg_results:
            return results

        indices = Snmp_v2c.extract_last_oid_index(sg_results)
        values = Snmp_v2c.snmp_get_result_value(sg_results)
        if not indices or not values:
            return results

        target = int(serving_group_id)
        limit = len(indices)
        if len(values) < limit:
            limit = len(values)

        matched_indices: list[int] = []
        for idx in range(limit):
            try:
                if int(values[idx]) != target:
                    continue
            except (TypeError, ValueError):
                continue
            matched_indices.append(int(indices[idx]))

        async def fetch_field(oid: str) -> str:
            try:
                raw = await self._snmp.get(oid)
            except Exception as exc:
                self.logger.error(f"SNMP get failed for {oid}: {exc}")
                return ""
            if not raw:
                return ""
            value = Snmp_v2c.get_result_value(raw)
            if value is None:
                return ""
            return str(value)

        for cm_index in matched_indices:
            mac = await fetch_field(f"docsIf3CmtsCmRegStatusMacAddr.{cm_index}")
            ipv4 = await fetch_field(f"docsIf3CmtsCmRegStatusIPv4Addr.{cm_index}")
            ipv6 = await fetch_field(f"docsIf3CmtsCmRegStatusIPv6Addr.{cm_index}")
            ipv6_ll = await fetch_field(f"docsIf3CmtsCmRegStatusIPv6LinkLocal.{cm_index}")

            if mac == "" and ipv4 == "" and ipv6 == "" and ipv6_ll == "":
                continue

            if not isinstance(mac, str) or mac == "":
                continue
            try:
                mac_value = MacAddress(mac)
            except (TypeError, ValueError):
                continue

            results.append(
                (
                    CableModemIndex(cm_index),
                    MacAddressStr(str(mac_value)),
                    IPv4Str(ipv4),
                    IPv6Str(ipv6),
                    IPv6LinkLocalStr(IPv6Str(ipv6_ll)),
                )
            )

        return results

    async def getCmInetAddress(
        self, mac: MacAddress
    ) -> tuple[MacAddressExist, RegisterCmInetAddress]:
        """
        Fetch CM inet addresses for a specific MAC address.
        """
        if not isinstance(mac, MacAddress):
            raise TypeError(f"mac must be MacAddress, got {type(mac).__name__}")

        mac_oid: str = "docsIf3CmtsCmRegStatusMacAddr"
        try:
            mac_results = await self._snmp.walk(mac_oid)
        except Exception as exc:
            self.logger.error(f"SNMP walk failed for {mac_oid}: {exc}")
            return (DEFAULT_MAC_ADDRESS_EXIST, EMPTY_REGISTER_CM_INET_ADDRESS)
        if not mac_results:
            return (DEFAULT_MAC_ADDRESS_EXIST, EMPTY_REGISTER_CM_INET_ADDRESS)

        mac_indices = Snmp_v2c.extract_last_oid_index(mac_results)
        mac_values = Snmp_v2c.snmp_get_result_bytes(mac_results)
        if not mac_indices or not mac_values:
            return (DEFAULT_MAC_ADDRESS_EXIST, EMPTY_REGISTER_CM_INET_ADDRESS)

        found_index: int | None = None
        limit = len(mac_indices)
        if len(mac_values) < limit:
            limit = len(mac_values)

        for idx in range(limit):
            if not isinstance(mac_values[idx], (bytes, str)):
                continue
            try:
                candidate = MacAddress(mac_values[idx])
            except (TypeError, ValueError):
                continue
            if candidate.is_equal(mac):
                found_index = int(mac_indices[idx])
                break

        if found_index is None:
            return (DEFAULT_MAC_ADDRESS_EXIST, EMPTY_REGISTER_CM_INET_ADDRESS)

        async def fetch_field(oid: str) -> str:
            try:
                raw = await self._snmp.get(oid)
            except Exception as exc:
                self.logger.error(f"SNMP get failed for {oid}: {exc}")
                return ""
            if not raw:
                return ""
            value = Snmp_v2c.get_result_value(raw)
            if value is None:
                return ""
            return str(value)

        ipv4_raw = await fetch_field(f"docsIf3CmtsCmRegStatusIPv4Addr.{found_index}")
        ipv6_raw = await fetch_field(f"docsIf3CmtsCmRegStatusIPv6Addr.{found_index}")
        ipv6_ll_raw = await fetch_field(
            f"docsIf3CmtsCmRegStatusIPv6LinkLocal.{found_index}"
        )
        if ipv4_raw == "" and ipv6_raw == "" and ipv6_ll_raw == "":
            async def fetch_field_walk(oid_base: str) -> str:
                try:
                    walk_results = await self._snmp.walk(oid_base)
                except Exception as exc:
                    self.logger.error(f"SNMP walk failed for {oid_base}: {exc}")
                    return ""
                if not walk_results:
                    return ""

                walk_indices = Snmp_v2c.extract_last_oid_index(walk_results)
                walk_values = Snmp_v2c.snmp_get_result_value(walk_results)
                if not walk_indices or not walk_values:
                    return ""

                limit = len(walk_indices)
                if len(walk_values) < limit:
                    limit = len(walk_values)

                for idx in range(limit):
                    if not isinstance(walk_indices[idx], (int, str)):
                        continue
                    try:
                        index_int = int(walk_indices[idx])
                    except (TypeError, ValueError):
                        continue
                    if index_int != found_index:
                        continue
                    return str(walk_values[idx])
                return ""

            ipv4_raw = await fetch_field_walk("docsIf3CmtsCmRegStatusIPv4Addr")
            ipv6_raw = await fetch_field_walk("docsIf3CmtsCmRegStatusIPv6Addr")
            ipv6_ll_raw = await fetch_field_walk("docsIf3CmtsCmRegStatusIPv6LinkLocal")

        def normalize_hex_inet(value: str) -> str:
            if not value.startswith("0x"):
                return value
            hex_str = value[2:]
            if len(hex_str) % 2 != 0:
                return value
            try:
                raw_bytes = bytes.fromhex(hex_str)
            except ValueError:
                return value
            if len(raw_bytes) == 4:
                return ".".join(str(byte) for byte in raw_bytes)
            if len(raw_bytes) == 16:
                parts = [
                    f"{raw_bytes[i] << 8 | raw_bytes[i + 1]:x}"
                    for i in range(0, 16, 2)
                ]
                return ":".join(parts)
            return value

        def validate_inet(value: str) -> IPv4Str | IPv6Str | IPv6LinkLocalStr:
            if value == "":
                return ""
            normalized = normalize_hex_inet(value)
            try:
                Inet(InetAddressStr(normalized))
            except ValueError:
                return ""
            return normalized

        ipv4_value = IPv4Str(validate_inet(ipv4_raw))
        ipv6_value = IPv6Str(validate_inet(ipv6_raw))
        ipv6_ll_value = IPv6LinkLocalStr(IPv6Str(validate_inet(ipv6_ll_raw)))

        return (
            MacAddressExist(True),
            (ipv4_value, ipv6_value, ipv6_ll_value),
        )

__all__ = [
    "CmtsOperation",
]

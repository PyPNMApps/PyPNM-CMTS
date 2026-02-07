# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import ipaddress
import logging

from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.docsis.cable_modem import CableModem
from pypnm.lib.inet import Inet
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import InetAddressStr, MacAddressStr

from pypnm_cmts.api.common.operations.models import OperationRequestContextModel
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.models import SgwCableModemModel
from pypnm_cmts.sgw.runtime_state import get_sgw_store
from pypnm_cmts.sgw.store import SgwCacheStore


class PnmModemResolver:
    """Common modem/IP resolution and CableModem construction helpers."""

    @staticmethod
    def resolve_modem_ip(
        sgw_store: SgwCacheStore | None,
        sg_id: ServiceGroupId,
        mac_address: MacAddressStr,
        logger: logging.Logger,
        log_prefix: str,
    ) -> tuple[InetAddressStr | None, SgwCacheStore | None]:
        store = sgw_store if sgw_store is not None else get_sgw_store()
        if store is None:
            logger.info(
                "%s [MODem_IP_UNRESOLVED] sg_id=%s mac=%s reason=sgw_store_missing",
                log_prefix,
                sg_id,
                mac_address,
            )
            return (None, sgw_store)
        entry = store.get_entry(sg_id)
        if entry is None:
            logger.info(
                "%s [MODem_IP_UNRESOLVED] sg_id=%s mac=%s reason=sg_entry_missing",
                log_prefix,
                sg_id,
                mac_address,
            )
            return (None, store)
        matched_modem = False
        for modem in entry.snapshot.cable_modems:
            if modem.mac != mac_address:
                continue
            matched_modem = True
            raw_ipv4 = str(modem.ipv4).strip()
            raw_ipv6 = str(modem.ipv6).strip()
            normalized_ipv4 = PnmModemResolver.normalize_ip_value(raw_ipv4)
            normalized_ipv6 = PnmModemResolver.normalize_ip_value(raw_ipv6)
            ip_value = PnmModemResolver.select_ip(modem)
            logger.info(
                "%s [MODem_IP_CANDIDATES] sg_id=%s mac=%s ipv4_raw=%s ipv4_norm=%s ipv6_raw=%s ipv6_norm=%s",
                log_prefix,
                sg_id,
                mac_address,
                raw_ipv4,
                normalized_ipv4,
                raw_ipv6,
                normalized_ipv6,
            )
            if ip_value is None:
                logger.info(
                    "%s [MODem_IP_UNRESOLVED] sg_id=%s mac=%s",
                    log_prefix,
                    sg_id,
                    mac_address,
                )
                return (None, store)
            try:
                return (InetAddressStr(str(Inet(ip_value))), store)
            except Exception:
                logger.info(
                    "%s [MODem_IP_INVALID] sg_id=%s mac=%s ip_selected=%s",
                    log_prefix,
                    sg_id,
                    mac_address,
                    ip_value,
                )
                return (None, store)
        if not matched_modem:
            logger.info(
                "%s [MODem_IP_UNRESOLVED] sg_id=%s mac=%s reason=modem_not_in_sg_snapshot",
                log_prefix,
                sg_id,
                mac_address,
            )
        return (None, store)

    @staticmethod
    def select_ip(modem: SgwCableModemModel) -> str | None:
        ipv4 = PnmModemResolver.normalize_ip_value(str(modem.ipv4))
        if ipv4 not in {"", "0.0.0.0"}:
            return ipv4
        ipv6 = PnmModemResolver.normalize_ip_value(str(modem.ipv6))
        if ipv6 not in {"", "::"}:
            return ipv6
        return None

    @staticmethod
    def normalize_ip_value(raw_value: str) -> str:
        value = raw_value.strip()
        if value == "":
            return ""
        if not value.startswith("0x"):
            return value
        return PnmModemResolver.decode_hex_ip(value)

    @staticmethod
    def decode_hex_ip(value: str) -> str:
        encoded = value[2:]
        if encoded == "":
            return ""
        try:
            if len(encoded) == 8:
                return str(ipaddress.IPv4Address(int(encoded, 16)))
            if len(encoded) == 32:
                return str(ipaddress.IPv6Address(int(encoded, 16)))
        except Exception:
            return value
        return value

    @staticmethod
    def resolve_write_community(context: OperationRequestContextModel | None) -> str:
        if context is None or context.snmp_write_community is None:
            return PnmConfigManager.get_write_community()
        return str(context.snmp_write_community)

    @staticmethod
    def build_cable_modem(
        mac_address: MacAddressStr,
        ip_address: InetAddressStr,
        write_community: str,
    ) -> CableModem:
        return CableModem(
            mac_address=MacAddress(mac_address),
            inet=Inet(InetAddressStr(ip_address)),
            write_community=write_community,
        )


__all__ = [
    "PnmModemResolver",
]


#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet
from pypnm.lib.mac_address import MacAddress
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.lib.types import MacAddressExist, RegisterCmInetAddress


class CmInetAddressCli:
    """
    CLI helper for fetching CM inet addresses by MAC address.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for CM inet address lookup.
        """
        parser = argparse.ArgumentParser(
            description="Fetch CM inet addresses by MAC address."
        )
        parser.add_argument(
            "--cmts-hostname",
            required=True,
            help="CMTS hostname or IP address.",
        )
        parser.add_argument(
            "--cmts-community",
            required=True,
            help="SNMPv2c community string.",
        )
        parser.add_argument(
            "--mac",
            required=True,
            help="Cable modem MAC address.",
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Include raw SNMP values for index and inet fields.",
        )
        parser.add_argument(
            "--text",
            action="store_true",
            help="Output in text format instead of JSON.",
        )
        return parser

    @staticmethod
    def resolve_inet(host: str) -> Inet:
        """
        Resolve a hostname or IP string into an Inet instance.
        """
        host_value = host.strip()
        if host_value == "":
            raise ValueError("CMTS hostname is empty.")

        try:
            return Inet(host_value)
        except ValueError as exc:
            endpoint = HostEndpoint(host_value)
            addresses = endpoint.resolve()
            if not addresses:
                raise ValueError(f"Failed to resolve hostname: {host_value}") from exc
            return Inet(addresses[0])

    @staticmethod
    async def fetch_inet_address(
        inet: Inet, community: str, mac: MacAddress
    ) -> tuple[MacAddressExist, RegisterCmInetAddress]:
        """
        Fetch inet addresses for a CM by MAC.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getCmInetAddress(mac)
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    async def fetch_raw_values(
        inet: Inet, community: str, mac: MacAddress
    ) -> dict[str, str | int]:
        """
        Fetch raw SNMP values for CM inet addresses by MAC.
        """
        snmp = Snmp_v2c(host=inet, community=community)
        mac_oid = "docsIf3CmtsCmRegStatusMacAddr"

        try:
            mac_results = await snmp.walk(mac_oid)
        except Exception as exc:
            raise RuntimeError(f"SNMP walk failed for {mac_oid}: {exc}") from exc
        if not mac_results:
            return {}

        mac_indices = Snmp_v2c.extract_last_oid_index(mac_results)
        mac_values = Snmp_v2c.snmp_get_result_bytes(mac_results)
        if not mac_indices or not mac_values:
            return {}

        found_index: int | None = None
        limit = len(mac_indices)
        if len(mac_values) < limit:
            limit = len(mac_values)

        for idx in range(limit):
            try:
                candidate = MacAddress(mac_values[idx])
            except (TypeError, ValueError):
                continue
            if candidate.is_equal(mac):
                found_index = int(mac_indices[idx])
                break

        if found_index is None:
            return {}

        async def fetch_field(oid: str) -> str:
            try:
                raw = await snmp.get(oid)
            except Exception as exc:
                raise RuntimeError(f"SNMP get failed for {oid}: {exc}") from exc
            if not raw:
                return ""
            value = Snmp_v2c.get_result_value(raw)
            if value is None:
                return ""
            return str(value)

        return {
            "mac_index": found_index,
            "mac_address": str(mac),
            "ipv4": await fetch_field(f"docsIf3CmtsCmRegStatusIPv4Addr.{found_index}"),
            "ipv6": await fetch_field(f"docsIf3CmtsCmRegStatusIPv6Addr.{found_index}"),
            "ipv6_link_local": await fetch_field(
                f"docsIf3CmtsCmRegStatusIPv6LinkLocal.{found_index}"
            ),
        }

    @staticmethod
    def render_output(
        mac: MacAddress,
        exists: MacAddressExist,
        inet_tuple: RegisterCmInetAddress,
        as_text: bool,
        raw_values: dict[str, str | int] | None,
    ) -> str:
        """
        Render output for CM inet address lookup.
        """
        ipv4, ipv6, ipv6_ll = inet_tuple
        if as_text:
            raw_suffix = ""
            if raw_values:
                raw_suffix = f" raw={raw_values}"
            return (
                f"mac_address={mac} exists={bool(exists)} "
                f"ipv4={ipv4} ipv6={ipv6} ipv6_ll={ipv6_ll}{raw_suffix}"
            )

        payload = {
            "mac_address": str(mac),
            "exists": bool(exists),
            "ipv4": str(ipv4),
            "ipv6": str(ipv6),
            "ipv6_link_local": str(ipv6_ll),
        }
        if raw_values is not None:
            payload["raw"] = raw_values
        return json.dumps(payload)

    @staticmethod
    def _emit_error(message: str) -> None:
        """
        Print an error message to stderr.
        """
        print(message, file=sys.stderr)

    @staticmethod
    def main() -> int:
        """
        CLI entry point for fetching CM inet addresses by MAC.
        """
        parser = CmInetAddressCli.build_parser()
        args = parser.parse_args()

        try:
            inet = CmInetAddressCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            CmInetAddressCli._emit_error(str(exc))
            return CmInetAddressCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            CmInetAddressCli._emit_error("SNMP community string is empty.")
            return CmInetAddressCli.EXIT_FAILURE

        try:
            mac = MacAddress(args.mac)
        except (TypeError, ValueError) as exc:
            CmInetAddressCli._emit_error(f"Invalid MAC address: {exc}")
            return CmInetAddressCli.EXIT_FAILURE

        raw_values: dict[str, str | int] | None = None
        try:
            exists, inet_tuple = asyncio.run(
                CmInetAddressCli.fetch_inet_address(inet, community, mac)
            )
            if args.raw:
                raw_values = asyncio.run(
                    CmInetAddressCli.fetch_raw_values(inet, community, mac)
                )
        except Exception as exc:
            CmInetAddressCli._emit_error(str(exc))
            return CmInetAddressCli.EXIT_FAILURE

        print(
            CmInetAddressCli.render_output(
                mac, exists, inet_tuple, args.text, raw_values
            )
        )

        if not bool(exists):
            return CmInetAddressCli.EXIT_FAILURE

        return CmInetAddressCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(CmInetAddressCli.main())

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
from pypnm.snmp.snmp_v2c import Snmp_v2c

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.lib.types import MdCmSgId, RegisterCmMacInetAddress


class RegisterCmMacInetCli:
    """
    CLI helper for fetching CM MAC + inet tuples for a serving group.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for CM MAC/inet lookup.
        """
        parser = argparse.ArgumentParser(
            description="Fetch CM MAC and IP addresses by serving group ID."
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
            "--serving-group-id",
            type=int,
            help="MD-CM-SG-ID to filter by. Omit to fetch all groups.",
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
    async def fetch_entries(
        inet: Inet, community: str, group_id: MdCmSgId
    ) -> list[RegisterCmMacInetAddress]:
        """
        Fetch CM MAC/inet tuples for a given serving group.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getAllRegisterCmMacInetAddress(group_id)
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    async def fetch_all_by_group(
        inet: Inet, community: str
    ) -> dict[int, list[RegisterCmMacInetAddress]]:
        """
        Fetch CM MAC/inet tuples for all serving groups.
        """
        snmp = Snmp_v2c(host=inet, community=community)
        results: dict[int, list[RegisterCmMacInetAddress]] = {}
        oid_base = "docsIf3CmtsCmRegStatusMdCmSgId"

        try:
            sg_results = await snmp.walk(oid_base)
        except Exception as exc:
            raise RuntimeError(f"SNMP walk failed for {oid_base}: {exc}") from exc
        if not sg_results:
            return results

        indices = Snmp_v2c.extract_last_oid_index(sg_results)
        values = Snmp_v2c.snmp_get_result_value(sg_results)
        if not indices or not values:
            return results

        limit = len(indices)
        if len(values) < limit:
            limit = len(values)

        by_group: dict[int, list[int]] = {}
        for idx in range(limit):
            try:
                group_id = int(values[idx])
                entry_index = int(indices[idx])
            except (TypeError, ValueError):
                continue
            by_group.setdefault(group_id, []).append(entry_index)

        operation = CmtsOperation(inet=inet, write_community=community, snmp=snmp)
        for group_id in by_group:
            results[group_id] = await operation.getAllRegisterCmMacInetAddress(
                MdCmSgId(group_id)
            )

        return results

    @staticmethod
    def render_output(
        entries: dict[int, list[RegisterCmMacInetAddress]], as_text: bool
    ) -> str:
        """
        Render output for CM MAC/inet results.
        """
        if not entries:
            if as_text:
                return "No entries found."
            return json.dumps({"entries": {}})

        if as_text:
            lines: list[str] = []
            for group_id, group_entries in entries.items():
                lines.append(f"serving_group_id={group_id}")
                for cm_index, mac, ipv4, ipv6, ipv6_ll in group_entries:
                    lines.append(
                        f"cm_index={cm_index} mac_address={mac} ipv4={ipv4} ipv6={ipv6} ipv6_ll={ipv6_ll}"
                    )
            return "\n".join(lines)

        payload: dict[str, list[dict[str, object]]] = {}
        for group_id, group_entries in entries.items():
            payload[str(group_id)] = []
            for cm_index, mac, ipv4, ipv6, ipv6_ll in group_entries:
                payload[str(group_id)].append(
                    {
                        "cm_index": int(cm_index),
                        "mac_address": str(mac),
                        "ipv4": str(ipv4),
                        "ipv6": str(ipv6),
                        "ipv6_link_local": str(ipv6_ll),
                    }
                )
        return json.dumps({"entries": payload})

    @staticmethod
    def _emit_error(message: str) -> None:
        """
        Print an error message to stderr.
        """
        print(message, file=sys.stderr)

    @staticmethod
    def main() -> int:
        """
        CLI entry point for fetching CM MAC/inet tuples.
        """
        parser = RegisterCmMacInetCli.build_parser()
        args = parser.parse_args()

        try:
            inet = RegisterCmMacInetCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            RegisterCmMacInetCli._emit_error(str(exc))
            return RegisterCmMacInetCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            RegisterCmMacInetCli._emit_error("SNMP community string is empty.")
            return RegisterCmMacInetCli.EXIT_FAILURE

        try:
            if args.serving_group_id is None:
                entries = asyncio.run(
                    RegisterCmMacInetCli.fetch_all_by_group(inet, community)
                )
            else:
                group_id = MdCmSgId(args.serving_group_id)
                group_entries = asyncio.run(
                    RegisterCmMacInetCli.fetch_entries(inet, community, group_id)
                )
                entries = {int(args.serving_group_id): group_entries}
        except Exception as exc:
            RegisterCmMacInetCli._emit_error(str(exc))
            return RegisterCmMacInetCli.EXIT_FAILURE

        print(RegisterCmMacInetCli.render_output(entries, args.text))

        if not entries:
            return RegisterCmMacInetCli.EXIT_FAILURE

        return RegisterCmMacInetCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(RegisterCmMacInetCli.main())

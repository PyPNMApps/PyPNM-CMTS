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

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.lib.types import CmtsCmRegStatusMacAddr


class CmRegStatusMacAddrCli:
    """
    CLI helper for fetching docsIf3CmtsCmRegStatusMacAddr entries.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for the CM registration status MAC CLI.
        """
        parser = argparse.ArgumentParser(
            description="Fetch docsIf3CmtsCmRegStatusMacAddr via SNMPv2c."
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
    async def fetch_reg_status_macs(
        inet: Inet, community: str
    ) -> list[CmtsCmRegStatusMacAddr]:
        """
        Fetch docsIf3CmtsCmRegStatusMacAddr entries from the CMTS.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getDocsIf3CmtsCmRegStatusMacAddr()
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(entries: list[CmtsCmRegStatusMacAddr], as_text: bool) -> str:
        """
        Render output for docsIf3CmtsCmRegStatusMacAddr results.
        """
        if not entries:
            if as_text:
                return "No entries found."
            return json.dumps({"entries": []})

        if as_text:
            lines: list[str] = []
            for reg_status_id, mac_addr in entries:
                lines.append(
                    f"reg_status_id={reg_status_id} mac_address={mac_addr}"
                )
            return "\n".join(lines)

        payload = []
        for reg_status_id, mac_addr in entries:
            payload.append(
                {
                    "reg_status_id": int(reg_status_id),
                    "mac_address": str(mac_addr),
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
        CLI entry point for fetching CM registration status MAC addresses.
        """
        parser = CmRegStatusMacAddrCli.build_parser()
        args = parser.parse_args()

        try:
            inet = CmRegStatusMacAddrCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            CmRegStatusMacAddrCli._emit_error(str(exc))
            return CmRegStatusMacAddrCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            CmRegStatusMacAddrCli._emit_error("SNMP community string is empty.")
            return CmRegStatusMacAddrCli.EXIT_FAILURE

        try:
            entries = asyncio.run(
                CmRegStatusMacAddrCli.fetch_reg_status_macs(inet, community)
            )
        except Exception as exc:
            CmRegStatusMacAddrCli._emit_error(str(exc))
            return CmRegStatusMacAddrCli.EXIT_FAILURE

        print(CmRegStatusMacAddrCli.render_output(entries, args.text))

        if not entries:
            return CmRegStatusMacAddrCli.EXIT_FAILURE

        return CmRegStatusMacAddrCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(CmRegStatusMacAddrCli.main())

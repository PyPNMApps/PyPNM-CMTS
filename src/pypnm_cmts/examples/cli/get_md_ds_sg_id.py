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
from pypnm_cmts.lib.types import MdNodeStatus


class MdDsSgIdCli:
    """
    CLI helper for fetching DocsIf3MdNodeStatusMdDsSgId entries.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for the DocsIf3MdNodeStatusMdDsSgId CLI.
        """
        parser = argparse.ArgumentParser(
            description="Fetch docsIf3MdNodeStatusMdDsSgId via SNMPv2c."
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
    async def fetch_md_ds_sg_id(inet: Inet, community: str) -> list[MdNodeStatus]:
        """
        Fetch DocsIf3MdNodeStatusMdDsSgId entries from the CMTS.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getDocsIf3MdNodeStatusMdDsSgId()
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(entries: list[MdNodeStatus], as_text: bool) -> str:
        """
        Render the output for the DocsIf3MdNodeStatusMdDsSgId results.
        """
        if not entries:
            if as_text:
                return "No entries found."
            return json.dumps({"entries": []})

        if as_text:
            lines: list[str] = []
            for interface_index, node_name, sg_id in entries:
                lines.append(
                    f"interface_index={interface_index} node_name={node_name} md_cm_sg_id={sg_id}"
                )
            return "\n".join(lines)

        payload = []
        for interface_index, node_name, sg_id in entries:
            payload.append(
                {
                    "interface_index": int(interface_index),
                    "node_name": str(node_name),
                    "md_cm_sg_id": int(sg_id),
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
        CLI entry point for fetching DocsIf3MdNodeStatusMdDsSgId.
        """
        parser = MdDsSgIdCli.build_parser()
        args = parser.parse_args()

        try:
            inet = MdDsSgIdCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            MdDsSgIdCli._emit_error(str(exc))
            return MdDsSgIdCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            MdDsSgIdCli._emit_error("SNMP community string is empty.")
            return MdDsSgIdCli.EXIT_FAILURE

        try:
            entries = asyncio.run(
                MdDsSgIdCli.fetch_md_ds_sg_id(inet, community)
            )
        except Exception as exc:
            MdDsSgIdCli._emit_error(str(exc))
            return MdDsSgIdCli.EXIT_FAILURE

        print(MdDsSgIdCli.render_output(entries, args.text))

        if not entries:
            return MdDsSgIdCli.EXIT_FAILURE

        return MdDsSgIdCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(MdDsSgIdCli.main())

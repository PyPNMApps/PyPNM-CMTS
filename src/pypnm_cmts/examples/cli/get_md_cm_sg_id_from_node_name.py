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
from pypnm_cmts.lib.types import MdCmSgId


class MdCmSgIdFromNodeNameCli:
    """
    CLI helper for fetching MD-CM-SG-ID from a node name.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for MD-CM-SG-ID lookup by node name.
        """
        parser = argparse.ArgumentParser(
            description="Fetch MD-CM-SG-ID by node name."
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
            "--node-name",
            required=True,
            help="MD node name (e.g., FN-1).",
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
    async def fetch_sg_id(
        inet: Inet, community: str, node_name: str
    ) -> tuple[bool, MdCmSgId]:
        """
        Fetch MD-CM-SG-ID for a given node name.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getMdCmSgIdFromNodeName(node_name)
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(
        node_name: str, exists: bool, sg_id: MdCmSgId, as_text: bool
    ) -> str:
        """
        Render output for MD-CM-SG-ID lookup.
        """
        if as_text:
            return f"node_name={node_name} exists={exists} md_cm_sg_id={sg_id}"

        payload = {
            "node_name": node_name,
            "exists": exists,
            "md_cm_sg_id": int(sg_id),
        }
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
        CLI entry point for MD-CM-SG-ID lookup by node name.
        """
        parser = MdCmSgIdFromNodeNameCli.build_parser()
        args = parser.parse_args()

        try:
            inet = MdCmSgIdFromNodeNameCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            MdCmSgIdFromNodeNameCli._emit_error(str(exc))
            return MdCmSgIdFromNodeNameCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            MdCmSgIdFromNodeNameCli._emit_error("SNMP community string is empty.")
            return MdCmSgIdFromNodeNameCli.EXIT_FAILURE

        node_name = args.node_name.strip()
        if node_name == "":
            MdCmSgIdFromNodeNameCli._emit_error("Node name is empty.")
            return MdCmSgIdFromNodeNameCli.EXIT_FAILURE

        try:
            exists, sg_id = asyncio.run(
                MdCmSgIdFromNodeNameCli.fetch_sg_id(inet, community, node_name)
            )
        except Exception as exc:
            MdCmSgIdFromNodeNameCli._emit_error(str(exc))
            return MdCmSgIdFromNodeNameCli.EXIT_FAILURE

        print(MdCmSgIdFromNodeNameCli.render_output(node_name, exists, sg_id, args.text))

        if not exists:
            return MdCmSgIdFromNodeNameCli.EXIT_FAILURE

        return MdCmSgIdFromNodeNameCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(MdCmSgIdFromNodeNameCli.main())

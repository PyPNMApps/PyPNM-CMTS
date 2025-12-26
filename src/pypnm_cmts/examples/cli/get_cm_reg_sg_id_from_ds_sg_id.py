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
from pypnm_cmts.lib.types import CmRegSgId, MdCmSgId


class CmRegSgIdFromDsSgIdCli:
    """
    CLI helper for fetching CM registration SG ID by DS SG ID.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for CM registration SG ID lookup by DS SG ID.
        """
        parser = argparse.ArgumentParser(
            description="Fetch CM registration SG ID by DS SG ID."
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
            "--ds-sg-id",
            required=True,
            type=int,
            help="Downstream SG ID value (e.g., 6, 10).",
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
        inet: Inet, community: str, ds_sg_id: MdCmSgId
    ) -> tuple[bool, CmRegSgId]:
        """
        Fetch CM registration SG ID for a given DS SG ID.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getCmRegStatusSgIdFromDsSgId(ds_sg_id)
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(
        ds_sg_id: MdCmSgId, exists: bool, sg_id: CmRegSgId, as_text: bool
    ) -> str:
        """
        Render output for CM registration SG ID lookup.
        """
        if as_text:
            return f"ds_sg_id={ds_sg_id} exists={exists} cm_reg_sg_id={sg_id}"

        payload = {
            "ds_sg_id": int(ds_sg_id),
            "exists": exists,
            "cm_reg_sg_id": int(sg_id),
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
        CLI entry point for CM registration SG ID lookup by DS SG ID.
        """
        parser = CmRegSgIdFromDsSgIdCli.build_parser()
        args = parser.parse_args()

        try:
            inet = CmRegSgIdFromDsSgIdCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            CmRegSgIdFromDsSgIdCli._emit_error(str(exc))
            return CmRegSgIdFromDsSgIdCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            CmRegSgIdFromDsSgIdCli._emit_error("SNMP community string is empty.")
            return CmRegSgIdFromDsSgIdCli.EXIT_FAILURE

        ds_sg_id = MdCmSgId(args.ds_sg_id)

        try:
            exists, sg_id = asyncio.run(
                CmRegSgIdFromDsSgIdCli.fetch_sg_id(inet, community, ds_sg_id)
            )
        except Exception as exc:
            CmRegSgIdFromDsSgIdCli._emit_error(str(exc))
            return CmRegSgIdFromDsSgIdCli.EXIT_FAILURE

        print(CmRegSgIdFromDsSgIdCli.render_output(ds_sg_id, exists, sg_id, args.text))

        if not exists:
            return CmRegSgIdFromDsSgIdCli.EXIT_FAILURE

        return CmRegSgIdFromDsSgIdCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(CmRegSgIdFromDsSgIdCli.main())

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
from pypnm_cmts.docsis.data_type.cmts_sysdescr import CmtsSysDescrModel


class SysDescrCli:
    """
    CLI helper for retrieving sysDescr from a CMTS via SNMPv2c.
    """

    DEFAULT_COMMUNITY = "public"
    DEFAULT_PORT = Snmp_v2c.SNMP_PORT

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for the sysDescr CLI example.

        Returns:
            argparse.ArgumentParser: Configured parser with host, community, and port options.
        """
        parser = argparse.ArgumentParser(
            description="Fetch sysDescr from a CMTS using SNMPv2c."
        )

        parser.add_argument(
            "host",
            help="CMTS IP address or resolvable hostname.",
        )
        parser.add_argument(
            "--read-community",
            default=SysDescrCli.DEFAULT_COMMUNITY,
            help="SNMPv2c read community string (default: public).",
        )
        parser.add_argument(
            "--write-community",
            default="",
            help="Optional SNMPv2c write community string (defaults to read community when empty).",
        )
        parser.add_argument(
            "-p",
            "--port",
            type=int,
            default=SysDescrCli.DEFAULT_PORT,
            help=f"SNMP port (default: {SysDescrCli.DEFAULT_PORT}).",
        )
        parser.add_argument(
            "--text",
            action="store_true",
            help="Output sysDescr as text instead of JSON.",
        )

        return parser

    @staticmethod
    def resolve_inet(host: str) -> Inet:
        """
        Resolve a hostname or IP string into an Inet instance.

        Args:
            host (str): Hostname or IP address.

        Returns:
            Inet: Parsed Inet instance from IP or resolved hostname.

        Raises:
            ValueError: If the input is empty or cannot be resolved.
        """
        host_value = host.strip()
        if host_value == "":
            raise ValueError("Host value is empty.")

        try:
            return Inet(host_value)
        except ValueError as exc:
            endpoint = HostEndpoint(host_value)
            addresses = endpoint.resolve()
            if not addresses:
                raise ValueError(f"Failed to resolve hostname: {host_value}") from exc
            return Inet(addresses[0])

    @staticmethod
    async def fetch_sysdescr(inet: Inet, community: str, port: int) -> CmtsSysDescrModel:
        """
        Fetch and parse sysDescr from the target CMTS.

        Args:
            inet (Inet): CMTS IP address.
            community (str): SNMP community string.
            port (int): SNMP port.

        Returns:
            SystemDescriptor: Parsed sysDescr data from the CMTS.
        """
        operation = CmtsOperation(inet=inet, write_community=community, port=port)
        return await operation.getSysDescr()

    @staticmethod
    def render_output(system_description: CmtsSysDescrModel, as_text: bool) -> str:
        """
        Render the sysDescr output string based on the chosen format.

        Args:
            system_description (SystemDescriptor): Parsed sysDescr data.
            as_json (bool): True for JSON output, False for text.

        Returns:
            str: Rendered sysDescr output.
        """
        if as_text:
            return str(system_description)
        payload = json.loads(system_description.to_json())
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
        CLI entry point for sysDescr retrieval.

        Returns:
            int: Process exit code (0 on success, 1 on failure).
        """
        parser = SysDescrCli.build_parser()
        args = parser.parse_args()

        try:
            inet = SysDescrCli.resolve_inet(args.host)
        except ValueError as exc:
            SysDescrCli._emit_error(str(exc))
            return SysDescrCli.EXIT_FAILURE

        read_community = args.read_community.strip()
        if read_community == "":
            SysDescrCli._emit_error("Community string is empty.")
            return SysDescrCli.EXIT_FAILURE
        try:
            system_description = asyncio.run(
                SysDescrCli.fetch_sysdescr(inet, read_community, args.port)
            )
        except Exception as exc:
            SysDescrCli._emit_error(f"SNMP request failed: {exc}")
            return SysDescrCli.EXIT_FAILURE

        print(SysDescrCli.render_output(system_description, args.text))

        if system_description.is_empty:
            return SysDescrCli.EXIT_FAILURE

        return SysDescrCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(SysDescrCli.main())

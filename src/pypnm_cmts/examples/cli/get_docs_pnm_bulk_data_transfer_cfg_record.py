#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from pypnm.lib.host_endpoint import HostEndpoint
from pypnm.lib.inet import Inet

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.pnm.data_type.bulk_data_transfer_cfg_entry import (
    DocsPnmBulkDataTransferCfgRecord,
)


class DocsPnmBulkDataTransferCfgCli:
    """CLI helper for docsPnmBulkDataTransferCfg table retrieval."""

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build the argument parser for docsPnmBulkDataTransferCfg lookup."""
        parser = argparse.ArgumentParser(
            description="Fetch docsPnmBulkDataTransferCfg table records."
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
        parser.add_argument(
            "--json-pretty",
            action="store_true",
            help="Pretty-print JSON output with indentation.",
        )
        return parser

    @staticmethod
    def resolve_inet(host: str) -> Inet:
        """Resolve a hostname or IP string into an Inet instance."""
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
    async def fetch_records(
        inet: Inet,
        community: str,
    ) -> list[DocsPnmBulkDataTransferCfgRecord]:
        """Fetch docsPnmBulkDataTransferCfg records from the CMTS."""
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getDocsPnmBulkDataTransferCfgRecord()
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(
        records: list[DocsPnmBulkDataTransferCfgRecord],
        as_text: bool,
        json_pretty: bool = False,
    ) -> str:
        """Render docsPnmBulkDataTransferCfg records as text or JSON."""
        if as_text:
            if not records:
                return "No entries found."
            lines = [
                f"index={record.index} entry={record.entry.model_dump(mode='json')}"
                for record in records
            ]
            return "\n".join(lines)

        payload = [record.model_dump(mode="json") for record in records]
        return json.dumps({"entries": payload}, indent=2 if json_pretty else None)

    @staticmethod
    def _emit_error(message: str) -> None:
        """Print an error message to stderr."""
        print(message, file=sys.stderr)

    @staticmethod
    def main() -> int:
        """CLI entry point for docsPnmBulkDataTransferCfg retrieval."""
        parser = DocsPnmBulkDataTransferCfgCli.build_parser()
        args = parser.parse_args()

        try:
            inet = DocsPnmBulkDataTransferCfgCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            DocsPnmBulkDataTransferCfgCli._emit_error(str(exc))
            return DocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            DocsPnmBulkDataTransferCfgCli._emit_error("SNMP community string is empty.")
            return DocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        try:
            records = asyncio.run(
                DocsPnmBulkDataTransferCfgCli.fetch_records(inet, community)
            )
        except Exception as exc:
            DocsPnmBulkDataTransferCfgCli._emit_error(str(exc))
            return DocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        print(DocsPnmBulkDataTransferCfgCli.render_output(records, args.text, args.json_pretty))
        if not records:
            return DocsPnmBulkDataTransferCfgCli.EXIT_FAILURE
        return DocsPnmBulkDataTransferCfgCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(DocsPnmBulkDataTransferCfgCli.main())

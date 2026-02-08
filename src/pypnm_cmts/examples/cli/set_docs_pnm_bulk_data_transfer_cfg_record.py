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
from pypnm_cmts.lib.constants import DocsPnmBulkDataTransferProtocol
from pypnm_cmts.pnm.data_type.bulk_data_transfer_cfg_entry import (
    DocsPnmBulkDataTransferCfgEntry,
)


def parse_bool_flag(value: str) -> bool:
    """Parse a CLI boolean string value."""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def parse_protocol(value: str) -> DocsPnmBulkDataTransferProtocol:
    """Parse protocol by integer or enum name."""
    normalized = value.strip().lower()
    by_name = {
        "tftp": DocsPnmBulkDataTransferProtocol.TFTP,
        "http": DocsPnmBulkDataTransferProtocol.HTTP,
        "https": DocsPnmBulkDataTransferProtocol.HTTPS,
    }
    if normalized in by_name:
        return by_name[normalized]
    return DocsPnmBulkDataTransferProtocol(int(value))


class SetDocsPnmBulkDataTransferCfgCli:
    """CLI helper for docsPnmBulkDataTransferCfg table updates."""

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build parser for docsPnmBulkDataTransferCfg set operations."""
        parser = argparse.ArgumentParser(
            description="Set writable docsPnmBulkDataTransferCfg table fields."
        )
        parser.add_argument(
            "--cmts-hostname",
            required=True,
            help="CMTS hostname or IP address.",
        )
        parser.add_argument(
            "--cmts-community-write",
            required=True,
            help="SNMPv2c write community string.",
        )
        parser.add_argument(
            "--index",
            required=True,
            type=int,
            help="Table row index.",
        )
        parser.add_argument(
            "--dest-hostname",
            help="Set docsPnmBulkDataTransferCfgDestHostname.",
        )
        parser.add_argument(
            "--dest-host-ip-addr-type",
            type=int,
            help="Set docsPnmBulkDataTransferCfgDestHostIpAddrType.",
        )
        parser.add_argument(
            "--dest-host-ip-address",
            help="Set docsPnmBulkDataTransferCfgDestHostIpAddress.",
        )
        parser.add_argument(
            "--dest-port",
            type=int,
            help="Set docsPnmBulkDataTransferCfgDestPort.",
        )
        parser.add_argument(
            "--dest-base-uri",
            help="Set docsPnmBulkDataTransferCfgDestBaseUri.",
        )
        parser.add_argument(
            "--protocol",
            type=parse_protocol,
            help="Set docsPnmBulkDataTransferCfgProtocol (tftp, http, https, or 1..3).",
        )
        parser.add_argument(
            "--local-store",
            type=parse_bool_flag,
            help="Set docsPnmBulkDataTransferCfgLocalStore (true or false).",
        )
        parser.add_argument(
            "--row-status",
            type=int,
            help="Set docsPnmBulkDataTransferCfgRowStatus.",
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
        """Resolve host string to an Inet address."""
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
    async def set_record(
        inet: Inet,
        community: str,
        index: int,
        entry: DocsPnmBulkDataTransferCfgEntry,
    ) -> bool:
        """Set docsPnmBulkDataTransferCfg writable fields for one row."""
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.setDocsPnmBulkDataTransferCfgRecord(index=index, entry=entry)
        except Exception as exc:
            raise RuntimeError(f"SNMP set failed: {exc}") from exc

    @staticmethod
    def build_entry(args: argparse.Namespace) -> DocsPnmBulkDataTransferCfgEntry:
        """Build typed entry from CLI args."""
        return DocsPnmBulkDataTransferCfgEntry(
            docsPnmBulkDataTransferCfgDestHostname=args.dest_hostname,
            docsPnmBulkDataTransferCfgDestHostIpAddrType=args.dest_host_ip_addr_type,
            docsPnmBulkDataTransferCfgDestHostIpAddress=args.dest_host_ip_address,
            docsPnmBulkDataTransferCfgDestPort=args.dest_port,
            docsPnmBulkDataTransferCfgDestBaseUri=args.dest_base_uri,
            docsPnmBulkDataTransferCfgProtocol=args.protocol,
            docsPnmBulkDataTransferCfgLocalStore=args.local_store,
            docsPnmBulkDataTransferCfgRowStatus=args.row_status,
        )

    @staticmethod
    def render_output(
        index: int,
        entry: DocsPnmBulkDataTransferCfgEntry,
        success: bool,
        as_text: bool,
        json_pretty: bool = False,
    ) -> str:
        """Render set operation result as text or JSON."""
        update_fields = entry.model_dump(mode="json", exclude_none=True)
        if as_text:
            return f"index={index} success={success} updates={update_fields}"
        payload = {"index": index, "success": success, "updates": update_fields}
        return json.dumps(payload, indent=2 if json_pretty else None)

    @staticmethod
    def emit_error(message: str) -> None:
        """Print error to stderr."""
        print(message, file=sys.stderr)

    @staticmethod
    def main() -> int:
        """CLI entry point."""
        parser = SetDocsPnmBulkDataTransferCfgCli.build_parser()
        args = parser.parse_args()

        try:
            inet = SetDocsPnmBulkDataTransferCfgCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            SetDocsPnmBulkDataTransferCfgCli.emit_error(str(exc))
            return SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        community = args.cmts_community_write.strip()
        if community == "":
            SetDocsPnmBulkDataTransferCfgCli.emit_error("SNMP community string is empty.")
            return SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        if args.index < 0:
            SetDocsPnmBulkDataTransferCfgCli.emit_error("index must be greater than or equal to zero.")
            return SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        try:
            entry = SetDocsPnmBulkDataTransferCfgCli.build_entry(args)
        except (TypeError, ValueError) as exc:
            SetDocsPnmBulkDataTransferCfgCli.emit_error(f"Invalid value: {exc}")
            return SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        if not entry.model_dump(exclude_none=True):
            SetDocsPnmBulkDataTransferCfgCli.emit_error("No settable fields provided.")
            return SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        try:
            success = asyncio.run(
                SetDocsPnmBulkDataTransferCfgCli.set_record(
                    inet=inet,
                    community=community,
                    index=args.index,
                    entry=entry,
                )
            )
        except Exception as exc:
            SetDocsPnmBulkDataTransferCfgCli.emit_error(str(exc))
            return SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE

        print(
            SetDocsPnmBulkDataTransferCfgCli.render_output(
                index=args.index,
                entry=entry,
                success=success,
                as_text=args.text,
                json_pretty=args.json_pretty,
            )
        )
        return SetDocsPnmBulkDataTransferCfgCli.EXIT_SUCCESS if success else SetDocsPnmBulkDataTransferCfgCli.EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(SetDocsPnmBulkDataTransferCfgCli.main())

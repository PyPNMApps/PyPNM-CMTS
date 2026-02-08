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
from pypnm.lib.mac_address import MacAddress
from pypnm.lib.types import MacAddressStr

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.pnm.data_type.ofdma_rxmer_entry import DocsPnmCmtsUsOfdmaRxMerEntry


def parse_bool_flag(value: str) -> bool:
    """Parse a CLI boolean string value."""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


class SetDocsPnmCmtsUsOfdmaRxMerCli:
    """CLI helper for docsPnmCmtsUsOfdmaRxMer table updates."""

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build parser for docsPnmCmtsUsOfdmaRxMer set operations."""
        parser = argparse.ArgumentParser(
            description="Set writable docsPnmCmtsUsOfdmaRxMer table fields."
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
            "--if-index",
            required=True,
            type=int,
            help="Table row ifIndex.",
        )
        parser.add_argument(
            "--enable",
            type=parse_bool_flag,
            help="Set docsPnmCmtsUsOfdmaRxMerEnable (true or false).",
        )
        parser.add_argument(
            "--cm-mac",
            help="Set docsPnmCmtsUsOfdmaRxMerCmMac.",
        )
        parser.add_argument(
            "--pre-eq",
            type=parse_bool_flag,
            help="Set docsPnmCmtsUsOfdmaRxMerPreEq (true or false).",
        )
        parser.add_argument(
            "--num-avgs",
            type=int,
            help="Set docsPnmCmtsUsOfdmaRxMerNumAvgs.",
        )
        parser.add_argument(
            "--file-name",
            help="Set docsPnmCmtsUsOfdmaRxMerFileName.",
        )
        parser.add_argument(
            "--destination-index",
            type=int,
            help="Set docsPnmCmtsUsOfdmaRxMerDestinationIndex.",
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
        entry: DocsPnmCmtsUsOfdmaRxMerEntry,
    ) -> bool:
        """Set docsPnmCmtsUsOfdmaRxMer writable fields for one row."""
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.setDocsPnmCmtsUsOfdmaRxMerRecord(index=index, entry=entry)
        except Exception as exc:
            raise RuntimeError(f"SNMP set failed: {exc}") from exc

    @staticmethod
    def build_entry(args: argparse.Namespace) -> DocsPnmCmtsUsOfdmaRxMerEntry:
        """Build typed entry from CLI args."""
        cm_mac: MacAddressStr | None = None
        if args.cm_mac is not None:
            cm_mac = MacAddressStr(str(MacAddress(args.cm_mac)))

        return DocsPnmCmtsUsOfdmaRxMerEntry(
            docsPnmCmtsUsOfdmaRxMerEnable=args.enable,
            docsPnmCmtsUsOfdmaRxMerCmMac=cm_mac,
            docsPnmCmtsUsOfdmaRxMerPreEq=args.pre_eq,
            docsPnmCmtsUsOfdmaRxMerNumAvgs=args.num_avgs,
            docsPnmCmtsUsOfdmaRxMerFileName=args.file_name,
            docsPnmCmtsUsOfdmaRxMerDestinationIndex=args.destination_index,
        )

    @staticmethod
    def render_output(
        index: int,
        entry: DocsPnmCmtsUsOfdmaRxMerEntry,
        success: bool,
        as_text: bool,
        json_pretty: bool = False,
    ) -> str:
        """Render set operation result as text or JSON."""
        update_fields = entry.model_dump(mode="json", exclude_none=True)
        if as_text:
            return f"if_index={index} success={success} updates={update_fields}"
        payload = {"if_index": index, "success": success, "updates": update_fields}
        return json.dumps(payload, indent=2 if json_pretty else None)

    @staticmethod
    def emit_error(message: str) -> None:
        """Print error to stderr."""
        print(message, file=sys.stderr)

    @staticmethod
    def main() -> int:
        """CLI entry point."""
        parser = SetDocsPnmCmtsUsOfdmaRxMerCli.build_parser()
        args = parser.parse_args()

        try:
            inet = SetDocsPnmCmtsUsOfdmaRxMerCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            SetDocsPnmCmtsUsOfdmaRxMerCli.emit_error(str(exc))
            return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE

        community = args.cmts_community_write.strip()
        if community == "":
            SetDocsPnmCmtsUsOfdmaRxMerCli.emit_error("SNMP community string is empty.")
            return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE

        if args.if_index < 0:
            SetDocsPnmCmtsUsOfdmaRxMerCli.emit_error("if-index must be greater than or equal to zero.")
            return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE

        try:
            entry = SetDocsPnmCmtsUsOfdmaRxMerCli.build_entry(args)
        except (TypeError, ValueError) as exc:
            SetDocsPnmCmtsUsOfdmaRxMerCli.emit_error(f"Invalid value: {exc}")
            return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE

        if not entry.model_dump(exclude_none=True):
            SetDocsPnmCmtsUsOfdmaRxMerCli.emit_error("No settable fields provided.")
            return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE

        try:
            success = asyncio.run(
                SetDocsPnmCmtsUsOfdmaRxMerCli.set_record(
                    inet=inet,
                    community=community,
                    index=args.if_index,
                    entry=entry,
                )
            )
        except Exception as exc:
            SetDocsPnmCmtsUsOfdmaRxMerCli.emit_error(str(exc))
            return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE

        print(
            SetDocsPnmCmtsUsOfdmaRxMerCli.render_output(
                index=args.if_index,
                entry=entry,
                success=success,
                as_text=args.text,
                json_pretty=args.json_pretty,
            )
        )
        return SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_SUCCESS if success else SetDocsPnmCmtsUsOfdmaRxMerCli.EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(SetDocsPnmCmtsUsOfdmaRxMerCli.main())

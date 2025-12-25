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

from pypnm_cmts.docsis.cmts_operation import CmtsOperation
from pypnm_cmts.lib.types import CmtsCmRegStatusMacAddr, MacAddressExist, MdCmSgId


class CmRegStatusSgIdViaMacCli:
    """
    CLI helper for looking up docsIf3CmtsCmRegStatusMdCmSgId by MAC address.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for the CM registration status SG ID lookup.
        """
        parser = argparse.ArgumentParser(
            description="Fetch docsIf3CmtsCmRegStatusMdCmSgId via MAC lookup."
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
    async def fetch_mac_entries(
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
    async def fetch_sg_id_for_mac(
        inet: Inet, community: str, mac: MacAddress
    ) -> tuple[MacAddressExist, MdCmSgId]:
        """
        Fetch docsIf3CmtsCmRegStatusMdCmSgId for the provided MAC address.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getdocsIf3CmtsCmRegStatusMdCmSgIdViaMacAddress(mac)
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(
        mac: MacAddress,
        reg_status_id: object,
        mac_exists: MacAddressExist,
        sg_id: MdCmSgId,
        as_text: bool,
    ) -> str:
        """
        Render output for the CM registration status SG ID lookup.
        """
        if as_text:
            return (
                f"mac_address={mac} reg_status_id={reg_status_id} "
                f"exists={bool(mac_exists)} md_cm_sg_id={sg_id}"
            )
        payload = {
            "mac_address": str(mac),
            "reg_status_id": int(reg_status_id),
            "exists": bool(mac_exists),
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
        CLI entry point for looking up docsIf3CmtsCmRegStatusMdCmSgId by MAC.
        """
        parser = CmRegStatusSgIdViaMacCli.build_parser()
        args = parser.parse_args()

        try:
            inet = CmRegStatusSgIdViaMacCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            CmRegStatusSgIdViaMacCli._emit_error(str(exc))
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            CmRegStatusSgIdViaMacCli._emit_error("SNMP community string is empty.")
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        try:
            entries = asyncio.run(
                CmRegStatusSgIdViaMacCli.fetch_mac_entries(inet, community)
            )
        except Exception as exc:
            CmRegStatusSgIdViaMacCli._emit_error(str(exc))
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        if not entries:
            CmRegStatusSgIdViaMacCli._emit_error("No MAC addresses found.")
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        reg_status_id, mac_str = entries[0]
        try:
            mac = MacAddress(str(mac_str))
        except (TypeError, ValueError) as exc:
            CmRegStatusSgIdViaMacCli._emit_error(f"Invalid MAC address: {exc}")
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        try:
            mac_exists, sg_id = asyncio.run(
                CmRegStatusSgIdViaMacCli.fetch_sg_id_for_mac(
                    inet, community, mac
                )
            )
        except Exception as exc:
            CmRegStatusSgIdViaMacCli._emit_error(str(exc))
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        print(
            CmRegStatusSgIdViaMacCli.render_output(
                mac, reg_status_id, mac_exists, sg_id, args.text
            )
        )

        if not bool(mac_exists):
            return CmRegStatusSgIdViaMacCli.EXIT_FAILURE

        return CmRegStatusSgIdViaMacCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(CmRegStatusSgIdViaMacCli.main())

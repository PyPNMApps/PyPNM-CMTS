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
from pypnm_cmts.docsis.data_type.cmts_service_group_topology import (
    CmtsServiceGroupTopologyModel,
)


class ServiceGroupTopologyCli:
    """
    CLI helper for fetching CMTS service-group topology entries.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for the service-group topology CLI.
        """
        parser = argparse.ArgumentParser(
            description="Fetch CMTS service-group topology via SNMPv2c."
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
    async def fetch_topology(
        inet: Inet,
        community: str,
    ) -> list[CmtsServiceGroupTopologyModel]:
        """
        Fetch service-group topology entries from the CMTS.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getServiceGroupTopology()
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def _entry_to_dict(entry: CmtsServiceGroupTopologyModel) -> dict[str, object]:
        return {
            "if_index": int(entry.if_index),
            "node_name": str(entry.node_name),
            "md_cm_sg_id": int(entry.md_cm_sg_id),
            "md_ds_sg_id": int(entry.md_ds_sg_id),
            "md_us_sg_id": int(entry.md_us_sg_id),
            "ds_exists": bool(entry.ds_exists),
            "us_exists": bool(entry.us_exists),
            "ds_ch_set_id": int(entry.ds_ch_set_id),
            "us_ch_set_id": int(entry.us_ch_set_id),
            "ds_channels": [int(ch) for ch in entry.ds_channels],
            "us_channels": [int(ch) for ch in entry.us_channels],
        }

    @staticmethod
    def render_output(
        entries: list[CmtsServiceGroupTopologyModel],
        as_text: bool,
    ) -> str:
        """
        Render the output for the service-group topology results.
        """
        if not entries:
            if as_text:
                return "No entries found."
            return json.dumps({"entries": []})

        if as_text:
            lines = [
                "if_index="
                f"{int(entry.if_index)} "
                "node_name="
                f"{entry.node_name} "
                "md_cm_sg_id="
                f"{int(entry.md_cm_sg_id)} "
                "md_ds_sg_id="
                f"{int(entry.md_ds_sg_id)} "
                "md_us_sg_id="
                f"{int(entry.md_us_sg_id)} "
                "ds_ch_set_id="
                f"{int(entry.ds_ch_set_id)} "
                "us_ch_set_id="
                f"{int(entry.us_ch_set_id)} "
                "ds_channels="
                f"{[int(ch) for ch in entry.ds_channels]} "
                "us_channels="
                f"{[int(ch) for ch in entry.us_channels]}"
                for entry in entries
            ]
            return "\n".join(lines)

        payload = [ServiceGroupTopologyCli._entry_to_dict(entry) for entry in entries]
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
        CLI entry point for fetching CMTS service-group topology.
        """
        parser = ServiceGroupTopologyCli.build_parser()
        args = parser.parse_args()

        try:
            inet = ServiceGroupTopologyCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            ServiceGroupTopologyCli._emit_error(str(exc))
            return ServiceGroupTopologyCli.EXIT_FAILURE

        try:
            entries = asyncio.run(
                ServiceGroupTopologyCli.fetch_topology(
                    inet,
                    args.cmts_community,
                )
            )
        except RuntimeError as exc:
            ServiceGroupTopologyCli._emit_error(str(exc))
            return ServiceGroupTopologyCli.EXIT_FAILURE

        output = ServiceGroupTopologyCli.render_output(entries, args.text)
        print(output)
        return ServiceGroupTopologyCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(ServiceGroupTopologyCli.main())

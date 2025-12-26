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
from pypnm_cmts.docsis.data_type.cmts_cm_reg_status_entry import (
    DocsIf3CmtsCmRegStatusEntry,
    DocsIf3CmtsCmRegStatusIdEntry,
)
from pypnm_cmts.lib.types import MdCmSgId


class AllRegisterCmCli:
    """
    CLI helper for fetching registered CM entries by serving group ID.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """
        Build the argument parser for the CM registration status lookup.
        """
        parser = argparse.ArgumentParser(
            description="Fetch CM registration entries by serving group ID."
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
            "--serving-group-id",
            type=int,
            help="Filter by MD-CM-SG-ID. If omitted, all groups are returned.",
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
    def _entry_to_dict(entry: DocsIf3CmtsCmRegStatusEntry) -> dict[str, object]:
        """
        Convert a registration entry to a JSON-serializable dict.
        """
        if hasattr(entry, "model_dump"):
            return entry.model_dump()  # type: ignore[no-any-return]
        return entry.dict()  # type: ignore[no-any-return]

    @staticmethod
    async def fetch_all_by_group(
        inet: Inet, community: str
    ) -> dict[int, list[DocsIf3CmtsCmRegStatusEntry]]:
        """
        Fetch registration entries for all serving groups.
        """
        snmp = Snmp_v2c(host=inet, community=community)
        results: dict[int, list[DocsIf3CmtsCmRegStatusEntry]] = {}
        oid_base = "docsIf3CmtsCmRegStatusMdCmSgId"

        try:
            sg_results = await snmp.walk(oid_base)
        except Exception as exc:
            raise RuntimeError(f"SNMP walk failed for {oid_base}: {exc}") from exc
        if not sg_results:
            return results

        indices = Snmp_v2c.extract_last_oid_index(sg_results)
        values = Snmp_v2c.snmp_get_result_value(sg_results)
        if not indices or not values:
            return results

        limit = len(indices)
        if len(values) < limit:
            limit = len(values)

        by_group: dict[int, list[int]] = {}
        for idx in range(limit):
            try:
                group_id = int(values[idx])
                entry_index = int(indices[idx])
            except (TypeError, ValueError):
                continue
            by_group.setdefault(group_id, []).append(entry_index)

        for group_id, entry_indices in by_group.items():
            try:
                entries = await DocsIf3CmtsCmRegStatusIdEntry.get_entries(
                    snmp, entry_indices
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to fetch CM registration entries for group {group_id}: {exc}"
                ) from exc
            results[group_id] = entries

        return results

    @staticmethod
    async def fetch_by_group(
        inet: Inet, community: str, group_id: MdCmSgId
    ) -> list[DocsIf3CmtsCmRegStatusEntry]:
        """
        Fetch registration entries for a single serving group.
        """
        operation = CmtsOperation(inet=inet, write_community=community)
        try:
            return await operation.getAllRegisterCm(group_id)
        except Exception as exc:
            raise RuntimeError(f"SNMP request failed: {exc}") from exc

    @staticmethod
    def render_output(
        entries: dict[int, list[DocsIf3CmtsCmRegStatusEntry]],
        as_text: bool,
    ) -> str:
        """
        Render output for CM registration entries.
        """
        if as_text:
            if not entries:
                return "No entries found."
            lines: list[str] = []
            for group_id, group_entries in entries.items():
                lines.append(f"serving_group_id={group_id}")
                lines.extend(str(entry) for entry in group_entries)
            return "\n".join(lines)

        payload: dict[str, list[dict[str, object]]] = {}
        for group_id, group_entries in entries.items():
            payload[str(group_id)] = [
                AllRegisterCmCli._entry_to_dict(entry) for entry in group_entries
            ]
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
        CLI entry point for fetching registered CM entries.
        """
        parser = AllRegisterCmCli.build_parser()
        args = parser.parse_args()

        try:
            inet = AllRegisterCmCli.resolve_inet(args.cmts_hostname)
        except ValueError as exc:
            AllRegisterCmCli._emit_error(str(exc))
            return AllRegisterCmCli.EXIT_FAILURE

        community = args.cmts_community.strip()
        if community == "":
            AllRegisterCmCli._emit_error("SNMP community string is empty.")
            return AllRegisterCmCli.EXIT_FAILURE

        entries: dict[int, list[DocsIf3CmtsCmRegStatusEntry]] = {}

        if args.serving_group_id is None:
            try:
                entries = asyncio.run(
                    AllRegisterCmCli.fetch_all_by_group(inet, community)
                )
            except Exception as exc:
                AllRegisterCmCli._emit_error(str(exc))
                return AllRegisterCmCli.EXIT_FAILURE
        else:
            try:
                results = asyncio.run(
                    AllRegisterCmCli.fetch_by_group(
                        inet, community, MdCmSgId(args.serving_group_id)
                    )
                )
            except Exception as exc:
                AllRegisterCmCli._emit_error(str(exc))
                return AllRegisterCmCli.EXIT_FAILURE
            entries = {int(args.serving_group_id): results}

        print(AllRegisterCmCli.render_output(entries, args.text))

        if not entries:
            return AllRegisterCmCli.EXIT_FAILURE

        return AllRegisterCmCli.EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(AllRegisterCmCli.main())

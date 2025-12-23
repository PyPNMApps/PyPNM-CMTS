#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import argparse
import json
from importlib import resources


class SystemJsonPrinter:
    """Print PyPNM-DOCSIS system.json content."""

    @staticmethod
    def load_system_json() -> dict[str, object]:
        """Load the PyPNM-DOCSIS system.json payload."""
        system_json = resources.files("pypnm.settings").joinpath("system.json")
        if not system_json.is_file():
            raise FileNotFoundError("pypnm-docsis system.json not found.")

        with system_json.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def run() -> int:
        """Run the CLI entry for printing system.json."""
        parser = argparse.ArgumentParser(
            description="Print PyPNM-DOCSIS system.json content."
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit raw JSON without additional formatting.",
        )

        args = parser.parse_args()
        data = SystemJsonPrinter.load_system_json()

        if args.json:
            print(json.dumps(data))
        else:
            print("PyPNM-DOCSIS system.json:")
            print(json.dumps(data, indent=2))

        return 0


if __name__ == "__main__":
    raise SystemExit(SystemJsonPrinter.run())

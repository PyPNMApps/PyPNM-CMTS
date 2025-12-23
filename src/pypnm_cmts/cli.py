#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import argparse

from pypnm_cmts.version import __version__

SUCCESS_EXIT_CODE = 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PyPNM-CMTS command line entry point."
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__version__}",
        help="Show PyPNM-CMTS version and exit.",
    )

    parser.parse_args()

    return SUCCESS_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())

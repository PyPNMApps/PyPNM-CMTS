#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.cli import _run_cli


def main() -> int:
    """
    Entry point for `python -m pypnm_cmts`.
    """
    return _run_cli()


if __name__ == "__main__":
    raise SystemExit(main())

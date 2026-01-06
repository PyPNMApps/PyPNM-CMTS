# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import sys

from pypnm_cmts.tools import release_tool


def main() -> int:
    sys.argv = [sys.argv[0], "--next", "build", *sys.argv[1:]]
    return release_tool.main()


if __name__ == "__main__":
    raise SystemExit(main())

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from enum import Enum


class CmtsPnmFileType(str, Enum):
    """CMTS-specific PNM file type identifiers."""

    US_OFDMA_RXMER_PER_SUBCARRIER = "PNNi"


__all__ = [
    "CmtsPnmFileType",
]

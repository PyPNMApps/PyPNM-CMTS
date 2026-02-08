# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from pypnm.snmp.snmp_v2c import Snmp_v2c


@dataclass(frozen=True)
class SnmpSetFieldSpec:
    """Typed description of a writable SNMP table field."""

    field: str
    value_type: Snmp_v2c.SnmpValueType
    encoder: Callable[[object], object] | None = None


class SnmpTableIo:
    """Shared SNMP table I/O helpers for CMTS PNM data type models."""

    @staticmethod
    def encode_truth_value(value: bool) -> int:
        """Encode SNMP TruthValue as true(1) / false(2)."""
        return 1 if value else 2

    @staticmethod
    def safe_cast(value: str, cast: Callable[[str], object]) -> object | None:
        """Safely cast a string value; return None on failure."""
        try:
            return cast(value)
        except Exception:
            return None

    @staticmethod
    async def fetch_field(
        *,
        snmp: Snmp_v2c,
        index: int,
        field: str,
        logger: logging.Logger,
        cast: Callable[[str], object] | None = None,
    ) -> object | None:
        """Fetch and coerce a single table field at index."""
        try:
            raw = await snmp.get(f"{field}.{index}")
            value = Snmp_v2c.get_result_value(raw)
            if value is None or value == "":
                return None
            if cast is not None:
                return SnmpTableIo.safe_cast(str(value), cast)

            text = str(value).strip()
            if text.isdigit():
                return int(text)
            if text.lower() in ("true", "false"):
                return text.lower() == "true"
            try:
                return float(text)
            except ValueError:
                return text
        except Exception as exc:
            logger.warning(f"Failed to fetch {field}.{index}: {exc}")
            return None

    @staticmethod
    async def set_fields(
        *,
        snmp: Snmp_v2c,
        index: int,
        updates: list[tuple[str, object]],
        field_specs: list[SnmpSetFieldSpec],
        logger: logging.Logger,
    ) -> bool:
        """Set table fields and return True only when all sets succeed."""
        spec_map = {spec.field: spec for spec in field_specs}
        for field, raw_value in updates:
            spec = spec_map.get(field)
            if spec is None:
                logger.warning("Missing SNMP set field spec for %s.%s", field, index)
                return False
            value = raw_value
            try:
                if spec.encoder is not None:
                    value = spec.encoder(raw_value)
                result = await snmp.set(f"{field}.{index}", value, spec.value_type)
                if not result:
                    logger.warning("SNMP set returned no result for %s.%s", field, index)
                    return False
            except Exception as exc:
                logger.warning("SNMP set failed for %s.%s: %s", field, index, exc)
                return False
        return True


__all__ = ["SnmpSetFieldSpec", "SnmpTableIo"]

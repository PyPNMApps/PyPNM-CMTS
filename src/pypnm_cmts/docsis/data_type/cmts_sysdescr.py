# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import re
from re import Pattern
from typing import ClassVar

from pydantic import BaseModel, Field


class CmtsSysDescrModel(BaseModel):
    """
    Pydantic model for CMTS sysDescr strings.
    """
    vendor: str = Field("", description="CMTS vendor.")
    platform: str = Field("", description="Platform or product family.")
    software: str = Field("", description="Software name or train.")
    version: str = Field("", description="Software version string.")
    release: str = Field("", description="Release label or channel.")
    compiled: str = Field("", description="Compile/build timestamp line.")
    raw: str = Field("", description="Raw sysDescr text.")
    is_empty: bool = Field(default=True, description="True if derived from an empty descriptor.")

    _CISCO_HEADER: ClassVar[str] = "Cisco IOS Software"
    _HARMONIC_HEADER: ClassVar[str] = "Harmonic"

    _CISCO_REGEX: ClassVar[Pattern[str]] = re.compile(
        r"Cisco IOS Software\s+\[(?P<train>[^]]+)\],\s+"
        r"(?P<platform>[^,]+),\s+Version\s+(?P<version>[^,]+),\s+"
        r"RELEASE SOFTWARE\s+\((?P<release>[^)]+)\)"
    )
    _HARMONIC_REGEX: ClassVar[Pattern[str]] = re.compile(
        r"^(?P<vendor>Harmonic)\s+(?P<platform>.+)$"
    )
    _HARMONIC_VERSION_REGEX: ClassVar[Pattern[str]] = re.compile(
        r"^(?P<software>\w+)\s+Software,\s+Released\s+Version\s+(?P<version>.+)$"
    )

    @classmethod
    def parse(cls, system_description: str) -> CmtsSysDescrModel:
        """
        Parse a CMTS sysDescr string into a structured model.
        """
        raw_value = cls._normalize_raw(system_description)
        if raw_value == "":
            return cls.empty()

        lines = [line.strip() for line in raw_value.splitlines() if line.strip()]
        header = lines[0] if lines else ""
        vendor_key = cls._detect_vendor(header)

        match vendor_key:
            case "cisco":
                return cls._parse_cisco(lines, raw_value)
            case "harmonic":
                return cls._parse_harmonic(lines, raw_value)
            case _:
                return cls(
                    raw=raw_value,
                    is_empty=False,
                )

    @classmethod
    def empty(cls) -> CmtsSysDescrModel:
        """
        Return an empty CMTS sysDescr model.
        """
        return cls(
            vendor="",
            platform="",
            software="",
            version="",
            release="",
            compiled="",
            raw="",
            is_empty=True,
        )

    @classmethod
    def _detect_vendor(cls, header: str) -> str:
        """
        Detect the vendor key from the sysDescr header line.
        """
        if header.startswith(cls._CISCO_HEADER):
            return "cisco"
        if header.startswith(cls._HARMONIC_HEADER):
            return "harmonic"
        return "unknown"

    @classmethod
    def _parse_cisco(cls, lines: list[str], raw_value: str) -> CmtsSysDescrModel:
        """
        Parse Cisco cBR sysDescr format.
        """
        match_line = lines[0] if lines else ""
        match = cls._CISCO_REGEX.search(match_line)
        compiled_line = cls._find_compiled_line(lines)

        if not match:
            return cls(raw=raw_value, compiled=compiled_line, is_empty=False)

        return cls(
            vendor="Cisco",
            platform=match.group("platform"),
            software=match.group("train"),
            version=match.group("version"),
            release=match.group("release"),
            compiled=compiled_line,
            raw=raw_value,
            is_empty=False,
        )

    @classmethod
    def _parse_harmonic(cls, lines: list[str], raw_value: str) -> CmtsSysDescrModel:
        """
        Parse Harmonic vCMTS sysDescr format.
        """
        header_line = lines[0] if lines else ""
        version_line = lines[1] if len(lines) > 1 else ""

        header_match = cls._HARMONIC_REGEX.search(header_line)
        version_match = cls._HARMONIC_VERSION_REGEX.search(version_line)
        compiled_line = cls._find_compiled_line(lines)

        vendor = header_match.group("vendor") if header_match else "Harmonic"
        platform = header_match.group("platform") if header_match else ""
        software = version_match.group("software") if version_match else ""
        version = version_match.group("version") if version_match else ""

        return cls(
            vendor=vendor,
            platform=platform,
            software=software,
            version=version,
            compiled=compiled_line,
            raw=raw_value,
            is_empty=False,
        )

    @classmethod
    def _find_compiled_line(cls, lines: list[str]) -> str:
        """
        Return the first line that begins with 'Compiled', if present.
        """
        for line in lines:
            if line.startswith("Compiled"):
                return line
        return ""

    @classmethod
    def _normalize_raw(cls, system_description: str) -> str:
        """
        Normalize the raw sysDescr string, including hex-encoded payloads.
        """
        raw_value = system_description.strip()
        if raw_value.startswith("0x"):
            hex_str = raw_value[2:]
            if len(hex_str) % 2 == 0:
                try:
                    raw_bytes = bytes.fromhex(hex_str)
                    return raw_bytes.decode("utf-8", errors="replace").strip()
                except ValueError:
                    return raw_value
        return raw_value

    def to_json(self) -> str:
        """
        Serialize the model to JSON.
        """
        return self.model_dump_json(exclude={"is_empty"})

    def __str__(self) -> str:
        """
        String representation of the CMTS sysDescr model.
        """
        if self.is_empty:
            return ""
        if self.vendor == "" and self.raw != "":
            return self.raw
        return (
            f"{self.vendor} {self.platform} {self.software} "
            f"Version {self.version} ({self.release}) {self.compiled}"
        ).strip()

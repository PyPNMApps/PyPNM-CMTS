# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import struct

from pydantic import BaseModel, ConfigDict, Field
from pypnm.lib.mac_address import MacAddress, MacAddressFormat
from pypnm.lib.types import InterfaceIndex, MacAddressStr, TimeStamp

from pypnm_cmts.pnm.parser.file_type import CmtsPnmFileType


class CmtsPnmHeaderParameters(BaseModel):
    """Typed fields parsed from a CMTS PNM header."""

    model_config = ConfigDict(extra="ignore")

    file_type: CmtsPnmFileType = Field(..., description="4-byte CMTS PNM file type.")
    major_version: int = Field(..., ge=0, description="Major version.")
    minor_version: int = Field(..., ge=0, description="Minor version.")
    capture_time: TimeStamp = Field(..., description="Capture timestamp in epoch seconds.")
    if_index: InterfaceIndex = Field(..., ge=0, description="IfIndex identifier.")
    unique_ccap_id: str = Field(..., description="Unique CCAP ID (decoded from 256-byte field).")
    rpd_id: MacAddressStr = Field(..., description="RPD identifier represented as 6-byte MAC.")
    rpd_port_number: int = Field(..., ge=0, description="RPD port number.")


class CmtsPnmHeader:
    """Base parser for CMTS PNM headers."""

    HEADER_FORMAT = "!4sBBI"
    EXTENDED_HEADER_V1_FORMAT = "!I256s"
    EXTENDED_HEADER_V2_SUFFIX_FORMAT = "!6sB"
    PNM_FILE_TYPE: CmtsPnmFileType | None = None

    def __init__(self, binary_data: bytes) -> None:
        self._header: CmtsPnmHeaderParameters
        self.pnm_data: bytes = b""
        self._parse_header(binary_data)

    def _parse_header(self, binary_data: bytes) -> None:
        header_size = struct.calcsize(self.HEADER_FORMAT)
        extended_v1_size = struct.calcsize(self.EXTENDED_HEADER_V1_FORMAT)
        minimum_size = header_size + extended_v1_size
        if len(binary_data) < minimum_size:
            raise ValueError("Binary data too short to contain CMTS PNM header.")

        file_type_raw, major_version, minor_version, capture_time = struct.unpack(
            self.HEADER_FORMAT, binary_data[:header_size]
        )
        file_type_str = file_type_raw.decode("ascii", errors="ignore")
        try:
            file_type = CmtsPnmFileType(file_type_str)
        except ValueError as exc:
            raise ValueError(f"Invalid CMTS PNM file type: {file_type_raw.hex()}") from exc

        if self.PNM_FILE_TYPE is not None and file_type != self.PNM_FILE_TYPE:
            expected = self.PNM_FILE_TYPE.value.encode("ascii").hex()
            actual = file_type_raw.hex()
            raise ValueError(f"Invalid file type: expected {expected}, got {actual}")

        v1_start = header_size
        v1_end = v1_start + extended_v1_size
        (
            if_index,
            unique_ccap_id_raw,
        ) = struct.unpack(
            self.EXTENDED_HEADER_V1_FORMAT,
            binary_data[v1_start:v1_end],
        )
        rpd_id_raw = bytes.fromhex("000000000000")
        rpd_port_number = 0
        payload_offset = v1_end
        if major_version >= 2:
            v2_suffix_size = struct.calcsize(self.EXTENDED_HEADER_V2_SUFFIX_FORMAT)
            if len(binary_data) < v1_end + v2_suffix_size:
                raise ValueError("Binary data too short to contain CMTS PNM v2+ RPD fields.")
            (
                rpd_id_raw,
                rpd_port_number,
            ) = struct.unpack(
                self.EXTENDED_HEADER_V2_SUFFIX_FORMAT,
                binary_data[v1_end : v1_end + v2_suffix_size],
            )
            payload_offset = v1_end + v2_suffix_size
        unique_ccap_id = unique_ccap_id_raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip()

        self._header = CmtsPnmHeaderParameters(
            file_type=file_type,
            major_version=major_version,
            minor_version=minor_version,
            capture_time=TimeStamp(capture_time),
            if_index=InterfaceIndex(if_index),
            unique_ccap_id=unique_ccap_id,
            rpd_id=MacAddress(rpd_id_raw).to_mac_format(MacAddressFormat.COLON),
            rpd_port_number=rpd_port_number,
        )
        self.pnm_data = binary_data[payload_offset:]

    def get_cmts_pnm_header_parameter_model(self) -> CmtsPnmHeaderParameters:
        """Return parsed CMTS PNM header parameters."""
        return self._header

    def getCmtsPnmHeaderParameterModel(self) -> CmtsPnmHeaderParameters:
        """Backward-compatible camelCase accessor for CMTS parser pattern consistency."""
        return self.get_cmts_pnm_header_parameter_model()


__all__ = [
    "CmtsPnmHeader",
    "CmtsPnmHeaderParameters",
]

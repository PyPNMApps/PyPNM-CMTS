# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import struct
from typing import cast

from pydantic import BaseModel, ConfigDict, Field
from pypnm.lib.constants import KHZ
from pypnm.lib.mac_address import MacAddress, MacAddressFormat
from pypnm.lib.signal_processing.shan.series import ShannonSeries
from pypnm.lib.types import (
    FloatSeries,
    FrequencyHz,
    FrequencySeriesHz,
    MacAddressStr,
)
from pypnm.pnm.lib.signal_statistics import SignalStatistics, SignalStatisticsModel

from pypnm_cmts.pnm.parser.cmts_pnm_header import CmtsPnmHeader, CmtsPnmHeaderParameters
from pypnm_cmts.pnm.parser.file_type import CmtsPnmFileType


class CmtsUsOfdmaRxMerPerSubcarrierHeaderModel(CmtsPnmHeaderParameters):
    """Header metadata for CMTS US OFDMA RxMER-per-subcarrier files."""

    model_config = ConfigDict(extra="ignore")


class CmtsUsOfdmaRxMerPerSubcarrierModel(BaseModel):
    """Canonical payload for CMTS upstream OFDMA RxMER per subcarrier captures."""

    model_config = ConfigDict(extra="ignore")

    pnm_header: CmtsUsOfdmaRxMerPerSubcarrierHeaderModel = Field(..., description="CMTS RxMER file header metadata.")
    mac_address: MacAddressStr      = Field(..., description="Cable modem MAC address.")
    number_of_averages: int         = Field(..., ge=0, description="Configured number of averages.")
    pre_eq_on: bool                 = Field(..., description="Pre-equalization flag.")
    subcarrier_zero_center_frequency: FrequencyHz   = Field(..., ge=0, description="Subcarrier zero center frequency (Hz).")
    first_active_subcarrier_index: int              = Field(..., ge=0, description="First active subcarrier index.")
    subcarrier_spacing: FrequencyHz                 = Field(..., ge=0, description="Subcarrier spacing (Hz).")
    data_length: int                                = Field(..., ge=0, description="Length in bytes of RxMER data.")
    occupied_channel_bandwidth: FrequencyHz         = Field(..., ge=0, description="OFDMA occupied bandwidth (Hz).")
    value_units: str                                = Field(default="dB", description="Non-mutable.")
    values: FloatSeries                             = Field(..., description="RxMER values per active subcarrier (dB).")
    signal_statistics: SignalStatisticsModel        = Field(..., description="Aggregate statistics computed from values.")
    modulation_statistics: dict[str, object]        = Field(..., description="Shannon-based modulation metrics.")


class CmtsUsOfdmaRxMerPerSubcarrier(CmtsPnmHeader):
    """Parser for CMTS US OFDMA RxMER-per-subcarrier binary files."""

    PNM_FILE_TYPE = CmtsPnmFileType.US_OFDMA_RXMER_PER_SUBCARRIER
    PAYLOAD_HEADER_FORMAT = "!6sHBIHBI"

    def __init__(self, binary_data: bytes) -> None:
        super().__init__(binary_data)
        self._rxmer_model: CmtsUsOfdmaRxMerPerSubcarrierModel
        self._header_model: CmtsUsOfdmaRxMerPerSubcarrierHeaderModel

        self._mac_address: MacAddressStr = MacAddress.null()
        self._number_of_averages: int = 0
        self._pre_eq_on: bool = False
        self._subcarrier_zero_center_frequency: FrequencyHz = FrequencyHz(0)
        self._first_active_subcarrier_index: int = 0
        self._subcarrier_spacing: FrequencyHz = FrequencyHz(0)
        self._rxmer_data_length: int = 0
        self._rxmer_data: bytes = b""
        self._rx_mer_float_data: FloatSeries = []

        self._process()

    def _process(self) -> None:
        self._header_model = CmtsUsOfdmaRxMerPerSubcarrierHeaderModel(
            **self.getCmtsPnmHeaderParameterModel().model_dump(),
        )

        payload_header_size = struct.calcsize(self.PAYLOAD_HEADER_FORMAT)
        if len(self.pnm_data) < payload_header_size:
            raise ValueError("Binary data too short to contain CMTS US OFDMA RxMER payload header.")

        (
            cm_mac_raw,
            self._number_of_averages,
            pre_eq_on_raw,
            self._subcarrier_zero_center_frequency,
            self._first_active_subcarrier_index,
            subcarrier_spacing_khz,
            self._rxmer_data_length,
        ) = struct.unpack(
            self.PAYLOAD_HEADER_FORMAT,
            self.pnm_data[:payload_header_size],
        )

        self._rxmer_data = self.pnm_data[payload_header_size : payload_header_size + self._rxmer_data_length]
        if len(self._rxmer_data) < self._rxmer_data_length:
            raise ValueError(
                f"Insufficient RxMER data length: {len(self._rxmer_data)} based on header field: {self._rxmer_data_length}"
            )

        self._mac_address = MacAddress(cm_mac_raw).to_mac_format(MacAddressFormat.COLON)
        self._pre_eq_on = bool(pre_eq_on_raw)
        self._subcarrier_zero_center_frequency = FrequencyHz(self._subcarrier_zero_center_frequency)
        self._subcarrier_spacing = FrequencyHz(subcarrier_spacing_khz * KHZ)

        self._rxmer_model = self._update_model()

    def _update_model(self) -> CmtsUsOfdmaRxMerPerSubcarrierModel:
        values = self.get_rxmer_values()
        return CmtsUsOfdmaRxMerPerSubcarrierModel(
            pnm_header=self._header_model,
            mac_address=self._mac_address,
            number_of_averages=self._number_of_averages,
            pre_eq_on=self._pre_eq_on,
            subcarrier_zero_center_frequency=self._subcarrier_zero_center_frequency,
            first_active_subcarrier_index=self._first_active_subcarrier_index,
            subcarrier_spacing=self._subcarrier_spacing,
            data_length=self._rxmer_data_length,
            occupied_channel_bandwidth=FrequencyHz(self._rxmer_data_length * self._subcarrier_spacing),
            values=values,
            signal_statistics=SignalStatistics(values).compute(),
            modulation_statistics=ShannonSeries(values).to_dict(),
        )

    def get_rxmer_values(self) -> FloatSeries:
        if self._rx_mer_float_data:
            return self._rx_mer_float_data
        if not self._rxmer_data:
            return []
        # quarter-dB encoded values.
        self._rx_mer_float_data = [min(max(byte / 4.0, 0.0), 63.5) for byte in self._rxmer_data]
        return self._rx_mer_float_data

    def get_frequencies(self) -> FrequencySeriesHz:
        spacing = int(self._subcarrier_spacing)
        first_idx = int(self._first_active_subcarrier_index)
        f_zero = int(self._subcarrier_zero_center_frequency)
        count = int(self._rxmer_data_length)
        if spacing <= 0 or count <= 0:
            return []
        start = f_zero + spacing * first_idx
        return cast(FrequencySeriesHz, [start + (i * spacing) for i in range(count)])

    def to_model(self) -> CmtsUsOfdmaRxMerPerSubcarrierModel:
        return self._rxmer_model

    def to_dict(self) -> dict[str, object]:
        return self._rxmer_model.model_dump()

    def to_json(self) -> str:
        return self._rxmer_model.model_dump_json()


__all__ = [
    "CmtsPnmFileType",
    "CmtsUsOfdmaRxMerPerSubcarrier",
    "CmtsUsOfdmaRxMerPerSubcarrierHeaderModel",
    "CmtsUsOfdmaRxMerPerSubcarrierModel",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import struct

from pypnm_cmts.pnm.parser import CmtsPnmFileType, CmtsUsOfdmaRxMerPerSubcarrier


def _build_blob() -> bytes:
    # CMTS file header: 4-byte file type + major + minor + capture time.
    cmts_header = struct.pack("!4sBBI", b"PNNi", 2, 0, 1700000000)

    if_index = 1001
    unique_ccap_id = b"ccap-01".ljust(256, b"\x00")
    rpd_id = bytes.fromhex("001122334455")
    rpd_port_number = 7
    cm_mac = bytes.fromhex("aabbccddeeff")
    number_of_averages = 64
    pre_eq_on = 1
    subcarrier_zero_frequency = 24_000_000
    first_active_subcarrier_index = 1
    subcarrier_spacing_khz = 50
    rxmer_raw = bytes([100, 120, 255, 0])  # 25.0, 30.0, 63.5(clamped), 0.0
    data_len = len(rxmer_raw)

    common_header = struct.pack("!I256s6sB", if_index, unique_ccap_id, rpd_id, rpd_port_number)
    payload_header = struct.pack(
        "!6sHBIHBI",
        cm_mac,
        number_of_averages,
        pre_eq_on,
        subcarrier_zero_frequency,
        first_active_subcarrier_index,
        subcarrier_spacing_khz,
        data_len,
    )
    return cmts_header + common_header + payload_header + rxmer_raw


def test_cmts_us_ofdma_rxmer_per_subcarrier_parser_smoke() -> None:
    parser = CmtsUsOfdmaRxMerPerSubcarrier(_build_blob())
    model = parser.to_model()

    assert model.pnm_header.file_type == CmtsPnmFileType.US_OFDMA_RXMER_PER_SUBCARRIER
    assert model.pnm_header.major_version == 2
    assert model.pnm_header.minor_version == 0
    assert model.pnm_header.if_index == 1001
    assert model.pnm_header.unique_ccap_id == "ccap-01"
    assert model.pnm_header.rpd_id == "00:11:22:33:44:55"
    assert model.pnm_header.rpd_port_number == 7
    assert model.mac_address == "aa:bb:cc:dd:ee:ff"
    assert model.number_of_averages == 64
    assert model.pre_eq_on is True
    assert model.subcarrier_zero_center_frequency == 24_000_000
    assert model.first_active_subcarrier_index == 1
    assert model.subcarrier_spacing == 50_000
    assert model.data_length == 4
    assert model.values == [25.0, 30.0, 63.5, 0.0]
    assert model.occupied_channel_bandwidth == 200_000

    freqs = parser.get_frequencies()
    assert freqs == [24_050_000, 24_100_000, 24_150_000, 24_200_000]


def test_cmts_us_ofdma_rxmer_per_subcarrier_parser_v1_defaults_rpd_fields() -> None:
    cmts_header = struct.pack("!4sBBI", b"PNNi", 1, 0, 1700000000)
    if_index = 1001
    unique_ccap_id = b"ccap-01".ljust(256, b"\x00")
    v1_header = struct.pack("!I256s", if_index, unique_ccap_id)

    cm_mac = bytes.fromhex("aabbccddeeff")
    number_of_averages = 64
    pre_eq_on = 1
    subcarrier_zero_frequency = 24_000_000
    first_active_subcarrier_index = 1
    subcarrier_spacing_khz = 50
    rxmer_raw = bytes([100, 120, 255, 0])
    data_len = len(rxmer_raw)

    payload_header = struct.pack(
        "!6sHBIHBI",
        cm_mac,
        number_of_averages,
        pre_eq_on,
        subcarrier_zero_frequency,
        first_active_subcarrier_index,
        subcarrier_spacing_khz,
        data_len,
    )
    parser = CmtsUsOfdmaRxMerPerSubcarrier(cmts_header + v1_header + payload_header + rxmer_raw)
    model = parser.to_model()

    assert model.pnm_header.major_version == 1
    assert model.pnm_header.rpd_id == "00:00:00:00:00:00"
    assert model.pnm_header.rpd_port_number == 0

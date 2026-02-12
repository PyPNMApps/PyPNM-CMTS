# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.api.routes.pnm.sg.ds.histogram.schemas import (
    DsHistogramServiceGroupStartCaptureRequest,
)


def test_histogram_start_capture_schema_does_not_expose_channel_ids() -> None:
    schema = DsHistogramServiceGroupStartCaptureRequest.model_json_schema()
    schema_text = str(schema)
    assert "channel_ids" not in schema_text
    assert "pnm_parameters.capture" not in schema_text


def test_histogram_start_capture_ignores_capture_payload() -> None:
    request = DsHistogramServiceGroupStartCaptureRequest.model_validate(
        {
            "cmts": {
                "serving_group": {"id": [1]},
                "cable_modem": {
                    "mac_address": ["aa:bb:cc:dd:ee:01"],
                    "pnm_parameters": {
                        "tftp": {"ipv4": None, "ipv6": None},
                        "capture": {"channel_ids": [194, 193]},
                    },
                },
            }
        }
    )
    assert request.cmts.cable_modem.pnm_parameters is not None
    assert request.cmts.cable_modem.pnm_parameters.tftp is not None
    assert "capture" not in request.cmts.cable_modem.pnm_parameters.model_dump()

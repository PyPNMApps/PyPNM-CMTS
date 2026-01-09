# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.lib.fastapi_constants import FAST_API_RESPONSE


def json_only_fast_api_response() -> dict[int, dict[str, object]]:
    """Return FAST_API_RESPONSE with JSON-only 200 content types."""
    responses: dict[int, dict[str, object]] = {}
    for status_code, detail in FAST_API_RESPONSE.items():
        if not isinstance(detail, dict):
            continue
        entry = dict(detail)
        if int(status_code) == 200:
            content = entry.get("content")
            if isinstance(content, dict):
                entry["content"] = {"application/json": content.get("application/json", {})}
            else:
                entry["content"] = {"application/json": {}}
        responses[int(status_code)] = entry
    return responses


JSON_ONLY_FAST_API_RESPONSE = json_only_fast_api_response()

__all__ = [
    "JSON_ONLY_FAST_API_RESPONSE",
    "json_only_fast_api_response",
]

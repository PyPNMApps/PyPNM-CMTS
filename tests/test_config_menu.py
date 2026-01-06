# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pypnm_cmts.tools.config_menu import CmtsConfigMenu


@pytest.mark.unit
def test_retrieval_method_updates_tftp_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "PnmFileRetrieval": {
            "retrieval_method": {
                "method": "tftp",
                "methods": {
                    "tftp": {
                        "host": "",
                        "port": 69,
                        "timeout": 5,
                        "remote_dir": "",
                    }
                },
            }
        }
    }
    config_path = tmp_path / "system.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    menu = CmtsConfigMenu(config_path=config_path)
    method_cfg = menu._ensure_nested_dict(menu.data, "PnmFileRetrieval").get("retrieval_method")
    assert isinstance(method_cfg, dict)

    prompts = {
        "TFTP host": "tftp.example",
        "TFTP port": "1069",
        "TFTP timeout": "7",
        "TFTP remote_dir": "/srv/tftp",
    }

    def _fake_prompt_str(label: str, _current: str) -> str:
        return prompts.get(label, "")

    def _fake_prompt_int(label: str, _current: object) -> int | None:
        value = prompts.get(label, "")
        if value == "":
            return None
        return int(value)

    monkeypatch.setattr(CmtsConfigMenu, "_prompt_str", staticmethod(_fake_prompt_str))
    monkeypatch.setattr(CmtsConfigMenu, "_prompt_int", staticmethod(_fake_prompt_int))

    menu._edit_retrieval_method_params(method_cfg, "tftp")
    method_block = method_cfg["methods"]["tftp"]

    assert method_block["host"] == "tftp.example"
    assert method_block["port"] == 1069
    assert method_block["timeout"] == 7
    assert method_block["remote_dir"] == "/srv/tftp"

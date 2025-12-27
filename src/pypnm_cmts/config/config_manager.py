# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

"""Configuration manager for PyPNM-CMTS settings access."""
from __future__ import annotations

import os

from pypnm.config.config_manager import ConfigManager

from pypnm_cmts.lib.types import CoordinationPath


class CmtsConfigManager:
    """Thin wrapper around the PyPNM config loader for CMTS settings."""

    def __init__(self, config_path: CoordinationPath | None = None) -> None:
        """Initialize the configuration loader."""
        resolved_path = os.fspath(config_path) if config_path is not None else None
        self._cfg = ConfigManager(config_path=resolved_path)

    def get(self, *keys: str) -> object | None:
        """Return the config value at the provided key path."""
        return self._cfg.get(*keys)

    def get_config_path(self) -> str:
        """Return the resolved configuration path."""
        return self._cfg.get_config_path()

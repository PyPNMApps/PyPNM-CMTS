# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
import logging
from pathlib import Path


class StartUp:
    """Initialize shared PyPNM-CMTS startup routines."""

    _LOGS_LINK_NAME = "logs"
    _logging_configured = False

    @staticmethod
    def initialize() -> bool:
        """Run startup initialization steps for PyPNM-CMTS."""
        StartUp._ensure_cmts_system_config()
        StartUp._configure_logging()
        StartUp._ensure_logs_symlink()
        return True

    @staticmethod
    def _configure_logging() -> None:
        """
        Configure logging using the installed pypnm-docsis settings.
        """
        if StartUp._logging_configured:
            return
        if logging.getLogger().handlers:
            StartUp._logging_configured = True
            return
        try:
            from pypnm.config.log_config import LoggerConfigurator
            from pypnm.config.system_config_settings import SystemConfigSettings
        except Exception:
            return

        LoggerConfigurator(
            log_dir=SystemConfigSettings.log_dir(),
            log_filename=SystemConfigSettings.log_filename(),
            level=SystemConfigSettings.log_level(),
            to_console=False,
            rotate=False,
        )
        StartUp._logging_configured = True

    @staticmethod
    def _ensure_logs_symlink() -> None:
        """
        Ensure the repo-level logs symlink points at the pypnm-docsis log directory.
        """
        log_dir = StartUp._resolve_pypnm_log_dir()
        if log_dir is None:
            return

        log_dir.mkdir(parents=True, exist_ok=True)
        project_root = StartUp._project_root()
        link_path = project_root / StartUp._LOGS_LINK_NAME

        if link_path.exists() and not link_path.is_symlink():
            return

        if link_path.is_symlink():
            try:
                if link_path.resolve() == log_dir.resolve():
                    return
                link_path.unlink()
            except Exception:
                return

        link_path.symlink_to(log_dir, target_is_directory=True)

    @staticmethod
    def _ensure_cmts_system_config() -> None:
        """
        Ensure the CMTS config block exists in the pypnm-docsis system.json file.
        """
        cmts_template_path = StartUp._cmts_template_path()
        if cmts_template_path is None or not cmts_template_path.exists():
            return

        system_config_path = StartUp._pypnm_system_config_path()
        if system_config_path is None or not system_config_path.exists():
            return

        try:
            template_data = json.loads(cmts_template_path.read_text(encoding="utf-8"))
            system_data = json.loads(system_config_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if not isinstance(template_data, dict) or not isinstance(system_data, dict):
            return

        updated = StartUp._merge_missing(system_data, template_data)
        if not updated:
            return

        system_config_path.write_text(json.dumps(system_data, indent=4) + "\n", encoding="utf-8")

    @staticmethod
    def _merge_missing(target: dict[str, object], template: dict[str, object]) -> bool:
        updated = False
        for key, value in template.items():
            if key not in target:
                target[key] = value
                updated = True
                continue
            target_value = target[key]
            if isinstance(target_value, dict) and isinstance(value, dict) and StartUp._merge_missing(target_value, value):
                updated = True
        return updated

    @staticmethod
    def _cmts_template_path() -> Path | None:
        """
        Resolve the CMTS template config path from the active package.
        """
        package_root = Path(__file__).resolve().parents[1]
        return package_root / "settings" / "cmts_system.json"

    @staticmethod
    def _pypnm_system_config_path() -> Path | None:
        """
        Resolve the system.json path from the installed pypnm-docsis package.
        """
        try:
            import sys

            import pypnm
        except Exception:
            return None

        package_root = StartUp._site_packages_root(sys.prefix)
        if package_root is None:
            package_root = Path(pypnm.__file__).resolve().parent

        return package_root / "settings" / "system.json"

    @staticmethod
    def _resolve_pypnm_log_dir() -> Path | None:
        """
        Resolve the log directory from the installed pypnm-docsis configuration.
        """
        try:
            import sys

            import pypnm
            from pypnm.config.system_config_settings import SystemConfigSettings
        except Exception:
            return None

        package_root = StartUp._site_packages_root(sys.prefix)
        if package_root is None:
            package_root = Path(pypnm.__file__).resolve().parent

        log_dir = Path(SystemConfigSettings.log_dir())
        if log_dir.is_absolute():
            return log_dir

        config_path = package_root / "settings" / "system.json"
        return (config_path.parent.parent / log_dir).resolve()

    @staticmethod
    def _site_packages_root(prefix: str) -> Path | None:
        """
        Return the site-packages path for the active virtual environment if present.
        """
        lib_dir = Path(prefix) / "lib"
        if not lib_dir.exists():
            return None

        for python_dir in lib_dir.glob("python*"):
            candidate = python_dir / "site-packages" / "pypnm"
            if candidate.exists():
                return candidate.resolve()

        return None

    @staticmethod
    def _project_root() -> Path:
        """
        Resolve the PyPNM-CMTS project root (parent of src/).
        """
        project_root = Path(__file__).resolve()
        while project_root.name != "src" and project_root != project_root.parent:
            project_root = project_root.parent
        if project_root.name == "src":
            return project_root.parent
        return project_root

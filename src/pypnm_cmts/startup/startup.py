# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path


class StartUp:
    """Initialize shared PyPNM-CMTS startup routines."""

    _LOGS_LINK_NAME = "logs"

    @staticmethod
    def initialize() -> bool:
        """Run startup initialization steps for PyPNM-CMTS."""
        StartUp._configure_logging()
        StartUp._ensure_logs_symlink()
        return True

    @staticmethod
    def _configure_logging() -> None:
        """
        Configure logging using the installed pypnm-docsis settings.
        """
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

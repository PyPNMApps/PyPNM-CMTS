# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from pypnm_cmts.config.config_manager import CmtsConfigManager
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings

JSON_INDENT_WIDTH = 4
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INVALID = 2


class ConfigValidationReport(BaseModel):
    """Validation result payload for config validation commands."""

    ok: bool = Field(default=False, description="Whether the configuration is valid.")
    errors: list[str] = Field(default_factory=list, description="Validation error messages.")


class CmtsConfigCommands:
    """Non-interactive configuration commands for system.json management."""

    _BASE_TEMPLATE = "system.json"
    _CMTS_TEMPLATE = "cmts_system.json"

    @staticmethod
    def resolve_config_path(path_value: str | None) -> Path:
        """Resolve the configuration path to use for config commands."""
        if path_value is not None and str(path_value).strip() != "":
            return Path(path_value)
        return Path(CmtsConfigManager().get_config_path())

    @staticmethod
    def _load_template(name: str) -> dict[str, object]:
        """Load a template JSON payload from the package settings."""
        template = resources.files("pypnm_cmts.settings").joinpath(name)
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {name}")
        with template.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Template is not a JSON object: {name}")
        return data

    @staticmethod
    def _merge_missing(target: dict[str, object], template: dict[str, object]) -> None:
        for key, value in template.items():
            if key not in target:
                target[key] = value
                continue
            target_value = target.get(key)
            if isinstance(target_value, dict) and isinstance(value, dict):
                CmtsConfigCommands._merge_missing(target_value, value)

    @classmethod
    def build_default_config(cls) -> dict[str, object]:
        """Build the base system.json payload with CMTS defaults merged."""
        data = cls._load_template(cls._BASE_TEMPLATE)
        cmts_data = cls._load_template(cls._CMTS_TEMPLATE)
        cls._merge_missing(data, cmts_data)
        return data

    @classmethod
    def init_config(
        cls,
        path: Path,
        force: bool,
        print_output: bool,
        dry_run: bool,
    ) -> int:
        """
        Initialize system.json with CMTS defaults when missing.

        Returns:
            int: Exit code (0 success, 1 error).
        """
        if path.exists() and not force:
            print(f"Config already exists at {path}. Use --force to overwrite.")
            return EXIT_ERROR
        data = cls.build_default_config()
        if print_output:
            print(json.dumps(data, indent=JSON_INDENT_WIDTH))
        if dry_run:
            return EXIT_OK
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{json.dumps(data, indent=JSON_INDENT_WIDTH)}\n", encoding="utf-8")
        return EXIT_OK

    @classmethod
    def validate_config(cls, path: Path, json_output: bool) -> int:
        """
        Validate system.json against CMTS orchestrator settings.

        Returns:
            int: Exit code (0 valid, 2 invalid, 1 error).
        """
        try:
            CmtsOrchestratorSettings.from_system_config(config_path=path)
        except ValidationError as exc:
            report = cls._build_validation_report(exc)
            cls._emit_validation(report, json_output)
            return EXIT_INVALID
        except (ValueError, FileNotFoundError) as exc:
            report = ConfigValidationReport(ok=False, errors=[str(exc)])
            cls._emit_validation(report, json_output)
            return EXIT_ERROR
        report = ConfigValidationReport(ok=True, errors=[])
        cls._emit_validation(report, json_output)
        return EXIT_OK

    @classmethod
    def show_config(cls, path: Path, pretty: bool) -> int:
        """
        Print the effective system.json with CMTS defaults merged.

        Returns:
            int: Exit code (0 success, 1 error).
        """
        if not path.exists():
            print(f"Config file not found at {path}")
            return EXIT_ERROR
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            print("Config file is not a JSON object.")
            return EXIT_ERROR
        cmts_data = cls._load_template(cls._CMTS_TEMPLATE)
        cls._merge_missing(data, cmts_data)
        indent = JSON_INDENT_WIDTH if pretty else None
        print(json.dumps(data, indent=indent))
        return EXIT_OK

    @staticmethod
    def _build_validation_report(exc: ValidationError) -> ConfigValidationReport:
        errors: list[str] = []
        for item in exc.errors():
            loc = item.get("loc", ())
            msg = item.get("msg", "validation error")
            field_path = ".".join(str(part) for part in loc) if loc else "value"
            errors.append(f"{field_path}: {msg}")
        return ConfigValidationReport(ok=False, errors=errors)

    @staticmethod
    def _emit_validation(report: ConfigValidationReport, json_output: bool) -> None:
        if json_output:
            print(report.model_dump_json())
            return
        if report.ok:
            print("Config validation succeeded.")
            return
        print("Config validation failed.")
        for error in report.errors:
            print(f"- {error}")

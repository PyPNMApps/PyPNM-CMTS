# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import json
import os
import subprocess
import sys
from enum import Enum
from pathlib import Path

import pypnm

from pydantic import BaseModel, Field, field_validator
from pypnm.lib.inet import Inet

from pypnm_cmts.config.config_manager import CmtsConfigManager

JSON_INDENT_WIDTH = 4


class RetrievalMethod(str, Enum):
    """Supported retrieval methods for PNM file retrieval."""

    LOCAL = "local"
    TFTP = "tftp"
    FTP = "ftp"
    SFTP = "sftp"
    HTTP = "http"
    HTTPS = "https"


class CmtsSnmpMenuModel(BaseModel):
    """Configuration input for CMTS SNMP v2c settings."""

    hostname: str = Field(default="", description="CMTS hostname or IP address.")
    read_community: str = Field(default="", description="SNMPv2c read community.")
    write_community: str = Field(default="", description="SNMPv2c write community.")


class CmSnmpMenuModel(BaseModel):
    """Configuration input for CM SNMP v2c settings."""

    read_community: str = Field(default="", description="SNMPv2c read community.")
    write_community: str = Field(default="", description="SNMPv2c write community.")


class CmtsTftpMenuModel(BaseModel):
    """Configuration input for CMTS TFTP defaults."""

    tftp_ipv4: str = Field(default="", description="TFTP server IPv4 address.")

    @field_validator("tftp_ipv4")
    @classmethod
    def _validate_tftp_ipv4(cls, value: str) -> str:
        if value == "":
            return value
        Inet(value)
        return value


class CmtsRetrievalMenuModel(BaseModel):
    """Configuration input for PNM file retrieval method selection."""

    method: RetrievalMethod | None = Field(default=None, description="PNM file retrieval method.")


class CmtsConfigMenu:
    """Interactive menu for editing PyPNM-CMTS system.json settings."""

    _CMTS_ROOT_KEY = "pypnm-cmts"
    _CMTS_LIST_KEY = "cmts"
    _CMTS_DEVICE_KEY = "device"
    _CMTS_SNMP_KEY = "SNMP"
    _CMTS_SNMP_VERSION_KEY = "version"
    _CMTS_SNMP_V2_KEY = "2c"

    _PNM_BULK_KEY = "PnmBulkDataTransfer"
    _PNM_TFTP_KEY = "tftp"
    _PNM_TFTP_IPV4_KEY = "ip_v4"

    _PNM_FILE_RETRIEVAL_KEY = "PnmFileRetrieval"
    _PNM_RETRIEVAL_METHOD_KEY = "retrieval_method"
    _PNM_RETRIEVAL_METHOD_FIELD = "method"

    _ORCH_KEY = "CmtsOrchestrator"
    _ORCH_ADAPTER_KEY = "adapter"

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = Path(CmtsConfigManager().get_config_path())
        self.config_path = config_path
        self.data: dict[str, object] = {}
        self._load()

    def run(self) -> int:
        """
        Run the interactive configuration menu.
        """
        if not self._interactive_allowed():
            print("Config menu requires an interactive terminal; skipping.")
            return 0

        while True:
            self._print_menu()
            try:
                choice = input("Enter selection: ").strip().lower()
            except KeyboardInterrupt:
                print("\n(CTRL-C ignored; use 'q' or Ctrl-D to exit)\n")
                continue
            except EOFError:
                choice = ""

            if choice in ("", "q", "quit", "x"):
                print("Exiting config menu.")
                return 0

            if choice == "1":
                self._run_cm_menu()
                continue

            if choice == "2":
                self._run_cmts_menu()
                continue

            if choice == "p":
                self._print_config()
                continue

            print("Invalid selection, please try again.\n")

    @staticmethod
    def _interactive_allowed() -> bool:
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            return False
        return sys.stdin.isatty()

    def _print_menu(self) -> None:
        print("\nPyPNM-CMTS Config Menu")
        print("=======================")
        print("Select an option:")
        print("  1) CM Config-Menu")
        print("  2) CMTS Config-Menu")
        print("  p) Print current system.json")
        print("  q) Quit")

    def _edit_snmp_menu(self) -> None:
        while True:
            print("\nSNMP Settings")
            print("=============")
            print("Select an option:")
            print("  1) CM SNMP Settings")
            print("  2) CMTS SNMP Settings")
            print("  p) Print Settings")
            print("  b) Back")
            print("Note: CM SNMP settings apply to all modems in the serving group.")
            try:
                choice = input("Enter selection: ").strip().lower()
            except KeyboardInterrupt:
                print("\n(CTRL-C ignored; use 'b' or Ctrl-D to exit)\n")
                continue
            except EOFError:
                choice = ""

            if choice in ("", "b", "back"):
                return
            if choice == "1":
                self._edit_cm_snmp()
                continue
            if choice == "2":
                self._edit_cmts_snmp()
                continue
            if choice == "p":
                self._print_config()
                continue

            print("Invalid selection, please try again.\n")

    def _print_cmts_menu(self) -> None:
        print("\nCMTS Config Menu")
        print("================")
        print("Select an option:")
        print("  1) CMTS Hostname")
        print("  2) Edit SNMP settings")
        print("  3) Edit PNM TFTP defaults")
        print("  4) Edit PNM file retrieval method")
        print("  p) Print current system.json")
        print("  b) Back")

    def _run_cm_menu(self) -> None:
        script_path = self._resolve_pypnm_tool("tools/system_config/menu.py")
        if script_path is None:
            print("\nPyPNM config menu not found. Set PYPNM_ROOT or install PyPNM.\n")
            return
        self._run_external_script(script_path)

    def _run_cmts_menu(self) -> None:
        while True:
            self._print_cmts_menu()
            try:
                choice = input("Enter selection: ").strip().lower()
            except KeyboardInterrupt:
                print("\n(CTRL-C ignored; use 'b' or Ctrl-D to exit)\n")
                continue
            except EOFError:
                choice = ""

            if choice in ("", "b", "back"):
                return
            if choice == "1":
                self._edit_cmts_hostname()
                continue
            if choice == "2":
                self._edit_snmp_menu()
                continue
            if choice == "3":
                self._edit_tftp()
                continue
            if choice == "4":
                self._edit_retrieval_method()
                continue
            if choice == "p":
                self._print_config()
                continue

            print("Invalid selection, please try again.\n")

    def _edit_cm_snmp(self) -> None:
        snmp = self._ensure_nested_dict(self.data, self._CMTS_SNMP_KEY)
        version = self._ensure_nested_dict(snmp, self._CMTS_SNMP_VERSION_KEY)
        v2c = self._ensure_nested_dict(version, self._CMTS_SNMP_V2_KEY)

        read_current = str(v2c.get("read_community", ""))
        write_current = str(v2c.get("write_community", ""))

        read_community = self._prompt_str("SNMPv2c read community", read_current)
        write_community = self._prompt_str("SNMPv2c write community", write_current)

        update = CmSnmpMenuModel(
            read_community=read_community,
            write_community=write_community,
        )

        if update.read_community != "":
            v2c["read_community"] = update.read_community
        if update.write_community != "":
            v2c["write_community"] = update.write_community

        self._save()

    def _edit_cmts_hostname(self) -> None:
        cmts_entry = self._ensure_cmts_entry()
        device = self._ensure_nested_dict(cmts_entry, self._CMTS_DEVICE_KEY)
        hostname_current = str(device.get("hostname", ""))
        hostname = self._prompt_str("CMTS hostname/IP", hostname_current)
        if hostname != "":
            device["hostname"] = hostname
            self._update_orchestrator_adapter(hostname=hostname)
        self._save()

    def _edit_cmts_snmp(self) -> None:
        cmts_entry = self._ensure_cmts_entry()
        device = self._ensure_nested_dict(cmts_entry, self._CMTS_DEVICE_KEY)
        snmp = self._ensure_nested_dict(cmts_entry, self._CMTS_SNMP_KEY)
        version = self._ensure_nested_dict(snmp, self._CMTS_SNMP_VERSION_KEY)
        v2c = self._ensure_nested_dict(version, self._CMTS_SNMP_V2_KEY)

        read_current = str(v2c.get("read_community", ""))
        write_current = str(v2c.get("write_community", ""))

        read_community = self._prompt_str("SNMPv2c read community", read_current)
        write_community = self._prompt_str("SNMPv2c write community", write_current)

        update = CmtsSnmpMenuModel(
            hostname="",
            read_community=read_community,
            write_community=write_community,
        )

        if update.read_community != "":
            v2c["read_community"] = update.read_community
        if update.write_community != "":
            v2c["write_community"] = update.write_community

        self._update_orchestrator_adapter(
            hostname=str(device.get("hostname", "")),
            community=v2c.get("read_community"),
            write_community=v2c.get("write_community"),
        )
        self._save()

    def _edit_tftp(self) -> None:
        pnm_bulk = self._ensure_nested_dict(self.data, self._PNM_BULK_KEY)
        tftp = self._ensure_nested_dict(pnm_bulk, self._PNM_TFTP_KEY)

        current_ipv4 = str(tftp.get(self._PNM_TFTP_IPV4_KEY, ""))
        tftp_ipv4 = self._prompt_str("TFTP server IPv4", current_ipv4)
        update = CmtsTftpMenuModel(tftp_ipv4=tftp_ipv4)
        if update.tftp_ipv4 != "":
            tftp[self._PNM_TFTP_IPV4_KEY] = update.tftp_ipv4

        self._save()

    def _edit_retrieval_method(self) -> None:
        script_path = self._resolve_pypnm_tool("tools/pnm/pnm_file_retrieval_setup.py")
        if script_path is not None:
            exit_code = self._run_external_script(script_path)
            if exit_code == 0:
                self._load()
            return

        retrieval = self._ensure_nested_dict(self.data, self._PNM_FILE_RETRIEVAL_KEY)
        method_cfg = self._ensure_nested_dict(retrieval, self._PNM_RETRIEVAL_METHOD_KEY)

        current_value = str(method_cfg.get(self._PNM_RETRIEVAL_METHOD_FIELD, ""))
        print("Available methods: local, tftp, ftp, sftp, http, https")
        method_input = self._prompt_str("Retrieval method", current_value)
        if method_input == "":
            return
        try:
            update = CmtsRetrievalMenuModel(method=RetrievalMethod(method_input))
        except ValueError:
            print("Invalid retrieval method selection.")
            return
        if update.method is not None:
            method_cfg[self._PNM_RETRIEVAL_METHOD_FIELD] = update.method.value
            self._edit_retrieval_method_params(method_cfg, update.method.value)

        self._save()

    def _print_config(self) -> None:
        if not self.config_path.exists():
            print(f"\nConfig file not found at {self.config_path}\n")
            return
        try:
            content = self.config_path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"\nFailed to read config: {exc}\n")
            return
        print("\nCurrent system.json:\n")
        print(content)
        print()

    def _load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        text = self.config_path.read_text(encoding="utf-8")
        self.data = json.loads(text)
        self._merge_cmts_template()

    def _save(self) -> None:
        text = json.dumps(self.data, indent=JSON_INDENT_WIDTH)
        self.config_path.write_text(f"{text}\n", encoding="utf-8")

    def _merge_cmts_template(self) -> None:
        template_path = Path(__file__).resolve().parents[1] / "settings" / "cmts_system.json"
        if not template_path.exists():
            return
        try:
            template_data = json.loads(template_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(template_data, dict) or not isinstance(self.data, dict):
            return
        self._merge_missing(self.data, template_data)

    def _edit_retrieval_method_params(self, method_cfg: dict[str, object], method: str) -> None:
        methods = self._ensure_nested_dict(method_cfg, "methods")
        method_block = self._ensure_nested_dict(methods, method)

        if method == RetrievalMethod.LOCAL.value:
            src_dir = self._prompt_str("Local src_dir", str(method_block.get("src_dir", "")))
            if src_dir != "":
                method_block["src_dir"] = src_dir
            return

        if method == RetrievalMethod.TFTP.value:
            host = self._prompt_str("TFTP host", str(method_block.get("host", "")))
            port = self._prompt_int("TFTP port", method_block.get("port"))
            timeout = self._prompt_int("TFTP timeout", method_block.get("timeout"))
            remote_dir = self._prompt_str("TFTP remote_dir", str(method_block.get("remote_dir", "")))
            if host != "":
                method_block["host"] = host
            if port is not None:
                method_block["port"] = port
            if timeout is not None:
                method_block["timeout"] = timeout
            if remote_dir != "":
                method_block["remote_dir"] = remote_dir
            return

        if method == RetrievalMethod.FTP.value:
            host = self._prompt_str("FTP host", str(method_block.get("host", "")))
            port = self._prompt_int("FTP port", method_block.get("port"))
            timeout = self._prompt_int("FTP timeout", method_block.get("timeout"))
            tls = self._prompt_bool("FTP TLS (true/false)", method_block.get("tls"))
            user = self._prompt_str("FTP user", str(method_block.get("user", "")))
            remote_dir = self._prompt_str("FTP remote_dir", str(method_block.get("remote_dir", "")))
            if host != "":
                method_block["host"] = host
            if port is not None:
                method_block["port"] = port
            if timeout is not None:
                method_block["timeout"] = timeout
            if tls is not None:
                method_block["tls"] = tls
            if user != "":
                method_block["user"] = user
            if remote_dir != "":
                method_block["remote_dir"] = remote_dir
            return

        if method == RetrievalMethod.SFTP.value:
            host = self._prompt_str("SFTP host", str(method_block.get("host", "")))
            port = self._prompt_int("SFTP port", method_block.get("port"))
            user = self._prompt_str("SFTP user", str(method_block.get("user", "")))
            private_key_path = self._prompt_str(
                "SFTP private_key_path", str(method_block.get("private_key_path", ""))
            )
            remote_dir = self._prompt_str("SFTP remote_dir", str(method_block.get("remote_dir", "")))
            if host != "":
                method_block["host"] = host
            if port is not None:
                method_block["port"] = port
            if user != "":
                method_block["user"] = user
            if private_key_path != "":
                method_block["private_key_path"] = private_key_path
            if remote_dir != "":
                method_block["remote_dir"] = remote_dir
            return

        if method == RetrievalMethod.HTTP.value:
            base_url = self._prompt_str("HTTP base_url", str(method_block.get("base_url", "")))
            port = self._prompt_int("HTTP port", method_block.get("port"))
            if base_url != "":
                method_block["base_url"] = base_url
            if port is not None:
                method_block["port"] = port
            return

        if method == RetrievalMethod.HTTPS.value:
            base_url = self._prompt_str("HTTPS base_url", str(method_block.get("base_url", "")))
            port = self._prompt_int("HTTPS port", method_block.get("port"))
            if base_url != "":
                method_block["base_url"] = base_url
            if port is not None:
                method_block["port"] = port

    def _update_orchestrator_adapter(
        self,
        hostname: str | None = None,
        community: str | None = None,
        write_community: str | None = None,
    ) -> None:
        orchestrator = self._ensure_nested_dict(self.data, self._ORCH_KEY)
        adapter = self._ensure_nested_dict(orchestrator, self._ORCH_ADAPTER_KEY)
        if hostname is not None and str(hostname).strip() != "":
            adapter["hostname"] = str(hostname)
        if community is not None and str(community).strip() != "":
            adapter["community"] = str(community)
        if write_community is not None and str(write_community).strip() != "":
            adapter["write_community"] = str(write_community)

    def _resolve_pypnm_tool(self, relative_path: str) -> Path | None:
        candidates: list[Path] = []
        package_root = Path(pypnm.__file__).resolve().parents[2]
        candidates.append(package_root)
        env_root = os.environ.get("PYPNM_ROOT", "").strip()
        if env_root != "":
            candidates.append(Path(env_root))
        repo_root = Path(__file__).resolve().parents[3]
        candidates.append(repo_root.parent / "PyPNM")
        for root in candidates:
            script_path = root / relative_path
            if script_path.exists():
                return script_path
        return None

    @staticmethod
    def _run_external_script(script_path: Path) -> int:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
        )
        if result.returncode != 0:
            print(f"\nScript exited with code {result.returncode}\n")
        else:
            print("\nScript completed successfully.\n")
        return result.returncode

    def _ensure_cmts_entry(self) -> dict[str, object]:
        root = self._ensure_nested_dict(self.data, self._CMTS_ROOT_KEY)
        cmts_list = root.get(self._CMTS_LIST_KEY)
        if not isinstance(cmts_list, list):
            cmts_list = []
            root[self._CMTS_LIST_KEY] = cmts_list
        if not cmts_list:
            cmts_list.append({})
        entry = cmts_list[0]
        if not isinstance(entry, dict):
            entry = {}
            cmts_list[0] = entry
        return entry

    @staticmethod
    def _ensure_nested_dict(data: dict[str, object], key: str) -> dict[str, object]:
        value = data.get(key)
        if isinstance(value, dict):
            return value
        data[key] = {}
        return data[key]

    @staticmethod
    def _merge_missing(target: dict[str, object], template: dict[str, object]) -> None:
        for key, value in template.items():
            if key not in target:
                target[key] = value
                continue
            target_value = target[key]
            if isinstance(target_value, dict) and isinstance(value, dict):
                CmtsConfigMenu._merge_missing(target_value, value)

    @staticmethod
    def _prompt_str(label: str, current: str) -> str:
        if current == "":
            prompt = f"{label} (currently unset, Enter to keep unset): "
        else:
            prompt = f"{label} [current: {current}] (Enter to keep): "
        value = input(prompt).strip()
        return value

    @staticmethod
    def _prompt_int(label: str, current: object) -> int | None:
        current_str = ""
        if isinstance(current, int):
            current_str = str(current)
        if current_str == "":
            prompt = f"{label} (currently unset, Enter to keep unset): "
        else:
            prompt = f"{label} [current: {current_str}] (Enter to keep): "
        value = input(prompt).strip()
        if value == "":
            return None
        try:
            return int(value)
        except ValueError:
            print("Invalid integer value; keeping existing.")
            return None

    @staticmethod
    def _prompt_bool(label: str, current: object) -> bool | None:
        current_str = ""
        if isinstance(current, bool):
            current_str = "true" if current else "false"
        if current_str == "":
            prompt = f"{label} (currently unset, Enter to keep unset): "
        else:
            prompt = f"{label} [current: {current_str}] (Enter to keep): "
        value = input(prompt).strip().lower()
        if value == "":
            return None
        if value in ("true", "t", "yes", "y", "1"):
            return True
        if value in ("false", "f", "no", "n", "0"):
            return False
        print("Invalid boolean value; keeping existing.")
        return None

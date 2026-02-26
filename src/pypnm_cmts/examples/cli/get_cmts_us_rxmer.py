#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class UsRxMerCliConfig:
    """Runtime configuration for the US OFDMA RxMER test CLI."""

    cmts_hostname: str
    ofdma_ifindex: int
    cm_mac: str
    read_community: str
    write_community: str
    tftp_ip: str
    tftp_ip_ccap: str
    tftp_path: str
    bdt_row: int
    filename: str
    pre_eq: int
    num_avgs: int
    poll_interval_seconds: float
    poll_timeout_seconds: float
    snmp_wrapper: str | None
    vendor_override: str


class CmtsUsRxMerCli:
    """
    US OFDMA RxMER trigger/poll test CLI for E6000, Casa, and Cisco cBR-8.
    """

    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1

    DEFAULT_SNMP_READ = os.environ.get("SNMP_READ", "public")
    DEFAULT_SNMP_WRITE = os.environ.get("SNMP_WRITE", "private")
    DEFAULT_TFTP_IP = os.environ.get("TFTP_IP", "172.16.6.101")
    DEFAULT_TFTP_IP_CCAP = os.environ.get("TFTP_IP_CCAP", "172.22.147.18")
    DEFAULT_TFTP_PATH = os.environ.get("TFTP_PATH", "./")
    DEFAULT_SNMP_WRAPPER = os.environ.get("SNMP_WRAPPER", "")

    PNM = "1.3.6.1.4.1.4491.2.1.27"

    OID_RXMER = f"{PNM}.1.3.7.1"
    OID_RXMER_ENABLE = f"{OID_RXMER}.1"
    OID_RXMER_CM_MAC = f"{OID_RXMER}.2"
    OID_RXMER_PRE_EQ = f"{OID_RXMER}.3"
    OID_RXMER_AVGS = f"{OID_RXMER}.4"
    OID_RXMER_STATUS = f"{OID_RXMER}.5"
    OID_RXMER_FILE = f"{OID_RXMER}.6"
    OID_RXMER_DEST = f"{OID_RXMER}.7"

    OID_BDT_E6000 = f"{PNM}.1.1.3.1.1"
    OID_BDT_CASA = f"{PNM}.1.1.1.5.1"
    OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"

    RS_DESTROY = 6
    RS_CREATE_AND_GO = 4

    MEAS_STATUS = {
        1: "other",
        2: "inactive",
        3: "busy",
        4: "sampleReady",
        5: "error",
        6: "resourceUnavailable",
        7: "sampleTruncated",
    }

    def __init__(self, config: UsRxMerCliConfig) -> None:
        self._config = config
        self._tftp_hex = self._ipv4_to_hex(config.tftp_ip)

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build the argument parser for the US OFDMA RxMER test CLI."""
        parser = argparse.ArgumentParser(
            description="Trigger and poll docsPnmCmtsUsOfdmaRxMerTable via SNMP."
        )
        parser.add_argument(
            "--cmts-hostname",
            required=True,
            help="CMTS hostname or IP address.",
        )
        parser.add_argument(
            "--ofdma-ifindex",
            required=True,
            type=int,
            help="docsIf index for the target OFDMA upstream channel.",
        )
        parser.add_argument(
            "--cm-mac",
            required=True,
            help="Cable modem MAC address (for example aa:bb:cc:dd:ee:ff).",
        )
        parser.add_argument(
            "--read-community",
            default=CmtsUsRxMerCli.DEFAULT_SNMP_READ,
            help=f"SNMPv2c read community (default: {CmtsUsRxMerCli.DEFAULT_SNMP_READ}).",
        )
        parser.add_argument(
            "--write-community",
            default=CmtsUsRxMerCli.DEFAULT_SNMP_WRITE,
            help=f"SNMPv2c write community (default: {CmtsUsRxMerCli.DEFAULT_SNMP_WRITE}).",
        )
        parser.add_argument(
            "--tftp-ip",
            default=CmtsUsRxMerCli.DEFAULT_TFTP_IP,
            help=f"E6000/legacy TFTP IPv4 target (default: {CmtsUsRxMerCli.DEFAULT_TFTP_IP}).",
        )
        parser.add_argument(
            "--tftp-ip-ccap",
            default=CmtsUsRxMerCli.DEFAULT_TFTP_IP_CCAP,
            help=f"Casa/Cisco TFTP IPv4 target (default: {CmtsUsRxMerCli.DEFAULT_TFTP_IP_CCAP}).",
        )
        parser.add_argument(
            "--tftp-path",
            default=CmtsUsRxMerCli.DEFAULT_TFTP_PATH,
            help=f"Casa BDT destination path (default: {CmtsUsRxMerCli.DEFAULT_TFTP_PATH}).",
        )
        parser.add_argument(
            "--bdt-row",
            type=int,
            default=1,
            help="BDT row index to provision for Cisco/E6000 (default: 1).",
        )
        parser.add_argument(
            "--filename",
            default="us_rxmer",
            help="RxMER filename prefix configured on the CMTS (default: us_rxmer).",
        )
        parser.add_argument(
            "--pre-eq",
            type=int,
            choices=(1, 2),
            default=1,
            help="RxMER pre-eq flag (1=true, 2=false; default: 1).",
        )
        parser.add_argument(
            "--num-avgs",
            type=int,
            default=1,
            help="RxMER NumAvgs value (default: 1).",
        )
        parser.add_argument(
            "--poll-interval-seconds",
            type=float,
            default=3.0,
            help="Polling interval for MeasStatus (default: 3.0).",
        )
        parser.add_argument(
            "--poll-timeout-seconds",
            type=float,
            default=120.0,
            help="Polling timeout for MeasStatus (default: 120.0).",
        )
        parser.add_argument(
            "--vendor",
            choices=("auto", "e6000", "casa", "cisco", "evo", "unknown"),
            default="auto",
            help="Override vendor detection for testing (default: auto).",
        )
        parser.add_argument(
            "--snmp-wrapper",
            default=CmtsUsRxMerCli.DEFAULT_SNMP_WRAPPER,
            help=(
                "Optional wrapper command template used to run SNMP tools remotely. "
                "Must include {cmd}, for example: ssh host docker exec lab {cmd}"
            ),
        )
        parser.add_argument(
            "--no-snmp-wrapper",
            action="store_true",
            help="Force local SNMP command execution (ignore --snmp-wrapper and SNMP_WRAPPER).",
        )
        return parser

    @staticmethod
    def build_config(args: argparse.Namespace) -> UsRxMerCliConfig:
        """Normalize parsed arguments into an immutable runtime config."""
        read_community = str(args.read_community).strip()
        write_community = str(args.write_community).strip()
        cmts_hostname = str(args.cmts_hostname).strip()
        cm_mac = str(args.cm_mac).strip()
        tftp_ip = str(args.tftp_ip).strip()
        tftp_ip_ccap = str(args.tftp_ip_ccap).strip()
        tftp_path = str(args.tftp_path)
        vendor_override = str(args.vendor).strip().lower()
        snmp_wrapper = None if args.no_snmp_wrapper else str(args.snmp_wrapper).strip() or None

        if cmts_hostname == "":
            raise ValueError("CMTS hostname is empty.")
        if cm_mac == "":
            raise ValueError("CM MAC is empty.")
        if read_community == "":
            raise ValueError("SNMP read community is empty.")
        if write_community == "":
            raise ValueError("SNMP write community is empty.")
        if args.num_avgs <= 0:
            raise ValueError("--num-avgs must be greater than 0.")
        if args.bdt_row <= 0:
            raise ValueError("--bdt-row must be greater than 0.")
        if args.poll_interval_seconds <= 0:
            raise ValueError("--poll-interval-seconds must be greater than 0.")
        if args.poll_timeout_seconds <= 0:
            raise ValueError("--poll-timeout-seconds must be greater than 0.")
        if snmp_wrapper is not None and "{cmd}" not in snmp_wrapper:
            raise ValueError("--snmp-wrapper must include {cmd}.")

        return UsRxMerCliConfig(
            cmts_hostname=cmts_hostname,
            ofdma_ifindex=int(args.ofdma_ifindex),
            cm_mac=cm_mac,
            read_community=read_community,
            write_community=write_community,
            tftp_ip=tftp_ip,
            tftp_ip_ccap=tftp_ip_ccap,
            tftp_path=tftp_path,
            bdt_row=int(args.bdt_row),
            filename=str(args.filename),
            pre_eq=int(args.pre_eq),
            num_avgs=int(args.num_avgs),
            poll_interval_seconds=float(args.poll_interval_seconds),
            poll_timeout_seconds=float(args.poll_timeout_seconds),
            snmp_wrapper=snmp_wrapper,
            vendor_override=vendor_override,
        )

    @staticmethod
    def main() -> int:
        """CLI entry point."""
        parser = CmtsUsRxMerCli.build_parser()
        args = parser.parse_args()
        try:
            config = CmtsUsRxMerCli.build_config(args)
            cli = CmtsUsRxMerCli(config)
            cli.run()
        except KeyboardInterrupt:
            print("\nInterrupted", file=sys.stderr)
            return CmtsUsRxMerCli.EXIT_FAILURE
        except Exception as exc:
            CmtsUsRxMerCli._emit_error(str(exc))
            return CmtsUsRxMerCli.EXIT_FAILURE
        return CmtsUsRxMerCli.EXIT_SUCCESS

    def run(self) -> None:
        """Run vendor detection, BDT setup, RxMER trigger, and polling."""
        self._step("0. Vendor detection")
        vendor, sysdescr = self.detect_vendor()
        print(f"  vendor   : {vendor}")
        print(f"  sysDescr : {sysdescr[:100]}")

        if vendor == "evo":
            print("\n  CommScope EVO vCCAP - coming soon.")
            return
        if vendor == "unknown":
            print("\n  Unknown vendor - proceeding with E6000 defaults. Check results carefully.")

        bdt_row = self._config.bdt_row
        if vendor == "cisco":
            self.configure_bdt_cisco(bdt_row)
        elif vendor == "casa":
            self._step("BDT discovery - reading Casa DestinationIndex")
            bdt_row = self.discover_dest_index_casa(self._config.ofdma_ifindex)
            self.configure_bdt_casa(bdt_row)
        elif vendor in {"e6000", "unknown"}:
            self.configure_bdt_e6000(bdt_row)

        try:
            self.configure_rxmer(self._config.ofdma_ifindex, self._config.cm_mac, bdt_row, vendor)
            self.poll(self._config.ofdma_ifindex)
        finally:
            print(f"\n  Stop  Enable=2  ofdma_ifindex={self._config.ofdma_ifindex}")
            result = self._snmpset(f"{self.OID_RXMER_ENABLE}.{self._config.ofdma_ifindex}", "i", 2)
            print(f"    {result}")

    def detect_vendor(self) -> tuple[str, str]:
        """Return (vendor, raw sysDescr) using sysDescr or explicit override."""
        if self._config.vendor_override != "auto":
            raw = self._snmpget(self.OID_SYS_DESCR)
            return (self._config.vendor_override, raw)

        raw = self._snmpget(self.OID_SYS_DESCR)
        low = raw.lower()
        if "cisco" in low or "cbr" in low:
            return ("cisco", raw)
        if "casa" in low:
            return ("casa", raw)
        if "arris" in low or "cer_v" in low:
            return ("e6000", raw)
        if "evo" in low or "vcmts" in low:
            return ("evo", raw)
        return ("unknown", raw)

    def configure_bdt_cisco(self, row: int) -> None:
        """Cisco cBR-8 BDT setup using docsPnmBulkDataTransferCfgTable."""
        tftp = self._config.tftp_ip_ccap
        tftp_hex = self._ipv4_to_hex(tftp)
        self._step(f"BDT row {row} - Cisco (docsPnmBulkDataTransferCfgTable) - TFTP {tftp}")
        self._snmpset(f"{self.OID_BDT_E6000}.9.{row}", "i", self.RS_DESTROY)
        time.sleep(2)
        print(f"  RowStatus.{row} = createAndGo(4)")
        result = self._snmpset(f"{self.OID_BDT_E6000}.9.{row}", "i", self.RS_CREATE_AND_GO)
        print(f"    {result}")
        time.sleep(1)
        fields = [
            (f"{self.OID_BDT_E6000}.3.{row}", "i", 1, "DestHostIpAddrType = ipv4(1)"),
            (f"{self.OID_BDT_E6000}.4.{row}", "x", tftp_hex, f"DestHostIpAddress  = {tftp}"),
            (f"{self.OID_BDT_E6000}.6.{row}", "s", f"tftp://{tftp}/", f"DestBaseUri        = tftp://{tftp}/"),
        ]
        for oid, value_type, value, desc in fields:
            print(f"  {desc}")
            result = self._snmpset(oid, value_type, value)
            print(f"    {result}")

    def configure_bdt_e6000(self, row: int) -> None:
        """E6000 BDT setup using docsPnmBulkDataTransferCfgTable."""
        self._step(f"BDT row {row} - E6000 (docsPnmBulkDataTransferCfgTable) - TFTP {self._config.tftp_ip}")
        fields = [
            (f"{self.OID_BDT_E6000}.9.{row}", "i", self.RS_CREATE_AND_GO, "RowStatus         = createAndGo(4)"),
            (f"{self.OID_BDT_E6000}.3.{row}", "i", 1, "DestHostIpAddrType = ipv4(1)"),
            (f"{self.OID_BDT_E6000}.4.{row}", "x", self._tftp_hex, f"DestHostIpAddress  = {self._config.tftp_ip}"),
        ]
        for oid, value_type, value, desc in fields:
            print(f"  {desc}")
            result = self._snmpset(oid, value_type, value)
            print(f"    {result}")

    def configure_bdt_casa(self, row: int) -> None:
        """Casa BDT setup using docsPnmCcapBulkDataControlTable."""
        tftp_ip = self._config.tftp_ip_ccap
        tftp_hex = self._ipv4_to_hex(tftp_ip)
        self._step(f"BDT CCAP row {row} - Casa (docsPnmCcapBulkDataControlTable) - TFTP {tftp_ip}")
        result = self._snmpset(f"{self.OID_BDT_CASA}.2.{row}", "i", 1)
        print(f"  DestIpAddrType = ipv4(1)  {result}")
        result = self._snmpset(f"{self.OID_BDT_CASA}.3.{row}", "x", tftp_hex)
        print(f"  DestIpAddr     = {tftp_ip}  {result}")
        result = self._snmpset(f"{self.OID_BDT_CASA}.4.{row}", "s", self._config.tftp_path)
        print(f"  DestPath       = {self._config.tftp_path}  {result}")
        result = self._snmpset(f"{self.OID_BDT_CASA}.5.{row}", "i", 3)
        print(f"  UploadControl  = autoUpload(3)  {result}")
        result = self._snmpset(f"{self.OID_BDT_CASA}.6.{row}", "x", "0x0400")
        print(f"  PnmTestSelector= 0x0400 (usOfdmaRxMer)  {result}")

    def discover_dest_index_casa(self, ofdma_ifindex: int) -> int:
        """Read docsPnmCmtsUsOfdmaRxMerDestinationIndex on Casa (read-only)."""
        raw = self._snmpget(f"{self.OID_RXMER_DEST}.{ofdma_ifindex}")
        value = self._parse_status_value(raw)
        if value > 0:
            print(f"  DestinationIndex (readback) = {value}")
            return value
        print(f"  DestinationIndex not set (raw={raw!r}) - defaulting to 1")
        return 1

    def configure_rxmer(self, ofdma_ifindex: int, cm_mac: str, dest_index: int, vendor: str) -> None:
        """Set RxMER parameters and trigger Enable=1."""
        idx = f".{ofdma_ifindex}"
        self._step(f"RxMER configure  ofdma_ifindex={ofdma_ifindex}  cm_mac={cm_mac}")

        mac_hex = cm_mac.replace(":", "").replace("-", "").upper()
        params: list[tuple[str, str, object, str]] = [
            (f"{self.OID_RXMER_CM_MAC}{idx}", "x", mac_hex, f"CmMac            = {cm_mac}"),
            (f"{self.OID_RXMER_FILE}{idx}", "s", self._config.filename, f"FileName         = {self._config.filename}"),
            (f"{self.OID_RXMER_PRE_EQ}{idx}", "i", self._config.pre_eq, f"PreEq            = {self._config.pre_eq}"),
            (f"{self.OID_RXMER_AVGS}{idx}", "u", self._config.num_avgs, f"NumAvgs          = {self._config.num_avgs}"),
        ]
        if vendor != "casa":
            params.append((f"{self.OID_RXMER_DEST}{idx}", "u", dest_index, f"DestinationIndex = {dest_index}"))

        for oid, value_type, value, desc in params:
            print(f"  {desc}")
            result = self._snmpset(oid, value_type, value)
            print(f"    {result}")
            time.sleep(0.05)

        self._step(f"Enable=1  (trigger)  ofdma_ifindex={ofdma_ifindex}")
        result = self._snmpset(f"{self.OID_RXMER_ENABLE}{idx}", "i", 1)
        print(f"  {result}")

    def poll(self, ofdma_ifindex: int) -> bool:
        """Poll docsPnmCmtsUsOfdmaRxMerMeasStatus until a terminal state."""
        self._step("Poll MeasStatus")
        started = time.time()
        while True:
            elapsed = time.time() - started
            if elapsed > self._config.poll_timeout_seconds:
                print(f"\n  timeout after {self._config.poll_timeout_seconds}s")
                return False

            raw = self._snmpget(f"{self.OID_RXMER_STATUS}.{ofdma_ifindex}")
            status_value = self._parse_status_value(raw)
            status_name = self.MEAS_STATUS.get(status_value, "unknown")
            print(f"  [{elapsed:5.1f}s]  MeasStatus={status_value} ({status_name})")

            if status_value == 4:
                print("\n  sampleReady - check TFTP server")
                return True
            if status_value == 7:
                print("\n  sampleTruncated")
                return True
            if status_value in (5, 6):
                print(f"\n  {status_name}")
                return False

            time.sleep(self._config.poll_interval_seconds)

    @staticmethod
    def _ipv4_to_hex(ipv4: str) -> str:
        octets = [part.strip() for part in ipv4.split(".")]
        if len(octets) != 4:
            raise ValueError(f"Invalid IPv4 address: {ipv4}")
        try:
            ints = [int(part) for part in octets]
        except ValueError as exc:
            raise ValueError(f"Invalid IPv4 address: {ipv4}") from exc
        if any(value < 0 or value > 255 for value in ints):
            raise ValueError(f"Invalid IPv4 address: {ipv4}")
        return "".join(f"{value:02X}" for value in ints)

    def _run_command(self, command: str) -> str:
        full_command = command
        if self._config.snmp_wrapper is not None:
            full_command = self._config.snmp_wrapper.format(cmd=command)
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        stdout = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                if "Cannot find module" not in line and "MIB search" not in line:
                    print(f"    stderr: {line}")
        return stdout

    def _snmpget(self, oid: str) -> str:
        command = (
            f"snmpget -v2c -c {shlex.quote(self._config.read_community)} "
            f"-Ov {shlex.quote(self._config.cmts_hostname)} {shlex.quote(oid)}"
        )
        return self._run_command(command)

    def _snmpset(self, oid: str, value_type: str, value: object) -> str:
        command = (
            f"snmpset -v2c -c {shlex.quote(self._config.write_community)} "
            f"{shlex.quote(self._config.cmts_hostname)} {shlex.quote(oid)} "
            f"{shlex.quote(value_type)} {shlex.quote(str(value))}"
        )
        return self._run_command(command)

    @staticmethod
    def _parse_status_value(raw: str) -> int:
        text = str(raw).strip()
        for token in reversed(text.replace(":", " ").split()):
            normalized = token.removeprefix("+").removeprefix("-")
            if normalized.isdigit():
                return int(token)
        return -1

    @staticmethod
    def _step(name: str) -> None:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"{'=' * 60}")

    @staticmethod
    def _emit_error(message: str) -> None:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(CmtsUsRxMerCli.main())

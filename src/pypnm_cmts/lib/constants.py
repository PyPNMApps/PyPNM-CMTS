# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from enum import Enum, IntEnum


class OperationalStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


class ReadinessCheck(str, Enum):
    STATE_DIR = "state_dir"
    STATE_DIR_CREATE = "state_dir_create"
    STATE_DIR_ACCESS = "state_dir_access"
    STATE_DIR_READ = "state_dir_read"
    WORKER_SG = "worker_sg"
    SGW_STARTUP = "sgw_startup"
    SGW_DISCOVERY = "sgw_discovery"
    SGW_PRIME = "sgw_prime"
    SGW_CACHE = "sgw_cache"


class CacheRefreshMode(str, Enum):
    NONE = "none"
    LIGHT = "light"
    HEAVY = "heavy"


class RfChannelType(str, Enum):
    SC_QAM = "sc_qam"
    OFDM = "ofdm"
    OFDMA = "ofdma"


class PnmCaptureStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PnmCaptureFailureReason(str, Enum):
    PER_MODEM_TIMEOUT = "per_modem_timeout"
    OVERALL_TIMEOUT = "overall_timeout"
    HTTP_ERROR = "http_error"
    PYPNM_ERROR = "pypnm_error"
    REQUEST_ERROR = "request_error"
    UNKNOWN = "unknown"


class OperationState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class OperationStage(str, Enum):
    ELIGIBILITY = "eligibility"
    PRECHECK = "precheck"
    CAPTURE = "capture"


class DocsPnmBulkDataTransferProtocol(IntEnum):
    TFTP = 1
    HTTP = 2
    HTTPS = 3


__all__ = [
    "CacheRefreshMode",
    "DocsPnmBulkDataTransferProtocol",
    "OperationStage",
    "OperationState",
    "OperationalStatus",
    "PnmCaptureFailureReason",
    "PnmCaptureStatus",
    "RfChannelType",
    "ReadinessCheck",
]

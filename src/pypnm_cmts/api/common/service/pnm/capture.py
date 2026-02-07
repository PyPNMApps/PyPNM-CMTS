# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.api.routes.common.extended.common_messaging_service import (
    MessagePayload,
    MessageResponse,
)
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.config.pnm_config_manager import PnmConfigManager
from pypnm.lib.inet import Inet
from pypnm.lib.types import FileNameStr, TimestampSec, TransactionId
from pypnm.lib.utils import Generate, TimeUnit

from pypnm_cmts.api.common.operations.models import OperationRequestContextModel
from pypnm_cmts.api.common.service.pnm.constants import (
    CLEAR_MESSAGE,
    MISSING_TRANSACTION_MESSAGE,
    NO_MESSAGE_RESPONSE,
)


class PnmCaptureHelper:
    """Common capture response parsing and timing helpers for PNM operations."""

    @staticmethod
    def resolve_tftp_servers(context: OperationRequestContextModel | None) -> tuple[Inet, Inet]:
        default_v4, default_v6 = PnmConfigManager.get_tftp_servers()
        ipv4 = default_v4 if context is None or context.tftp_ipv4 is None else Inet(str(context.tftp_ipv4))
        ipv6 = default_v6 if context is None or context.tftp_ipv6 is None else Inet(str(context.tftp_ipv6))
        return (ipv4, ipv6)

    @staticmethod
    def parse_capture_response(
        response: MessageResponse | None,
        expected_message_type: str,
        no_message_response: str = NO_MESSAGE_RESPONSE,
        missing_transaction_message: str = MISSING_TRANSACTION_MESSAGE,
    ) -> tuple[ServiceStatusCode, TransactionId | None, FileNameStr | None, str]:
        if response is None:
            return (ServiceStatusCode.FAILURE, None, None, no_message_response)
        status_code = response.status
        if status_code != ServiceStatusCode.SUCCESS:
            return (status_code, None, None, f"{status_code.name}")
        payload = response.payload
        if not isinstance(payload, list):
            return (ServiceStatusCode.FAILURE, None, None, missing_transaction_message)
        for element in payload:
            message_type, message = PnmCaptureHelper.extract_payload_entry(element)
            if message_type != expected_message_type:
                continue
            if not isinstance(message, dict):
                continue
            transaction_id = message.get("transaction_id")
            filename = message.get("filename")
            if transaction_id is None or filename is None:
                continue
            return (
                status_code,
                TransactionId(str(transaction_id)),
                FileNameStr(str(filename)),
                CLEAR_MESSAGE,
            )
        return (ServiceStatusCode.PNM_FILE_TRANSACTION_ID_NOT_FOUND, None, None, missing_transaction_message)

    @staticmethod
    def extract_payload_entry(
        element: MessagePayload | dict[str, object],
    ) -> tuple[str | None, object | None]:
        if isinstance(element, MessagePayload):
            return (element.message_type, element.message)
        if isinstance(element, dict):
            message_type = element.get("message_type")
            message = element.get("message")
            return (
                str(message_type) if message_type is not None else None,
                message,
            )
        return (None, None)

    @staticmethod
    def now_epoch() -> TimestampSec:
        return TimestampSec(Generate.time_stamp(unit=TimeUnit.SECONDS))


__all__ = [
    "PnmCaptureHelper",
]


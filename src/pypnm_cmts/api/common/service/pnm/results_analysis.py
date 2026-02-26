# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import cpu_count

from pydantic import BaseModel, Field
from pypnm.api.routes.common.classes.analysis.analysis import Analysis
from pypnm.api.routes.common.classes.file_capture.pnm_file_transaction import (
    PnmFileTransaction,
)
from pypnm.api.routes.docs.pnm.files.service import PnmFileService
from pypnm.lib.file_processor import FileProcessor
from pypnm.lib.types import TransactionId
from pypnm.pnm.parser.pnm_file_type import PnmFileType
from pypnm.pnm.parser.pnm_parameter import GetPnmParserAndParameters


class PnmStoredCaptureAnalysisResultModel(BaseModel):
    """Decoded basic analysis result for a stored PNM transaction."""

    transaction_id: TransactionId = Field(..., description="Transaction identifier used to load the PNM file.")
    pnm_file_type: str | None = Field(default=None, description="Resolved PNM file type name.")
    system_description: dict[str, object] | None = Field(default=None, description="System description from transaction metadata.")
    analysis: dict[str, object] | None = Field(default=None, description="Decoded basic analysis payload.")
    error: str | None = Field(default=None, description="Decode/analysis error message if analysis failed.")


class PnmStoredCaptureAnalysisService:
    """Threaded decoder/analyzer for stored PNM transaction files."""

    def __init__(
        self,
        pnm_file_service: PnmFileService | None = None,
        max_workers: int | None = None,
    ) -> None:
        self._pnm_file_service = pnm_file_service or PnmFileService()
        self._pnm_file_transaction = PnmFileTransaction()
        self._max_workers = max_workers if max_workers is not None else max(1, min(8, cpu_count() or 1))
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_transactions_basic(
        self,
        transaction_ids: list[TransactionId],
    ) -> dict[TransactionId, PnmStoredCaptureAnalysisResultModel]:
        """Decode and analyze stored transactions using PyPNM basic analysis helpers."""
        unique_transaction_ids = self._dedupe_transaction_ids(transaction_ids)
        if not unique_transaction_ids:
            return {}

        if len(unique_transaction_ids) == 1:
            result = self._analyze_transaction_basic(unique_transaction_ids[0])
            return {result.transaction_id: result}

        results: dict[TransactionId, PnmStoredCaptureAnalysisResultModel] = {}
        worker_count = min(self._max_workers, len(unique_transaction_ids))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(self._analyze_transaction_basic, transaction_id): transaction_id
                for transaction_id in unique_transaction_ids
            }
            for future in as_completed(future_map):
                transaction_id = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive guard
                    self.logger.warning(
                        "[ANALYZE_TXN_BASIC_FAIL] tx_id=%s error=%s",
                        transaction_id,
                        exc,
                    )
                    result = PnmStoredCaptureAnalysisResultModel(
                        transaction_id=transaction_id,
                        error=f"analysis unavailable for transaction {transaction_id}: {exc}",
                    )
                results[transaction_id] = result
        return results

    def _analyze_transaction_basic(
        self,
        transaction_id: TransactionId,
    ) -> PnmStoredCaptureAnalysisResultModel:
        try:
            system_description = self._load_system_description(transaction_id)
            pnm_path = self._pnm_file_service.get_pnm_path_for_transaction(transaction_id)
            parser, parser_params = GetPnmParserAndParameters(FileProcessor(pnm_path).read_file()).get_parser()
            parser_model = parser.to_model()
            analysis_model = self._dispatch_basic_analysis(parser_params.file_type, parser_model)
            payload = analysis_model.model_dump() if hasattr(analysis_model, "model_dump") else None
            if not isinstance(payload, dict):
                return PnmStoredCaptureAnalysisResultModel(
                    transaction_id=transaction_id,
                    pnm_file_type=parser_params.file_type.name,
                    system_description=system_description,
                    error=f"analysis payload is not a JSON object for transaction {transaction_id}",
                )
            return PnmStoredCaptureAnalysisResultModel(
                transaction_id=transaction_id,
                pnm_file_type=parser_params.file_type.name,
                system_description=system_description,
                analysis=payload,
            )
        except Exception as exc:
            self.logger.warning(
                "[ANALYZE_TXN_BASIC_FAIL] tx_id=%s error=%s",
                transaction_id,
                exc,
            )
            return PnmStoredCaptureAnalysisResultModel(
                transaction_id=transaction_id,
                error=f"analysis unavailable for transaction {transaction_id}: {exc}",
            )

    def _load_system_description(
        self,
        transaction_id: TransactionId,
    ) -> dict[str, object] | None:
        record = self._pnm_file_transaction.get_record(transaction_id)
        if not isinstance(record, dict):
            return None
        device_details = record.get(PnmFileTransaction.DEVICE_DETAILS)
        if not isinstance(device_details, dict):
            return None
        system_description = device_details.get("system_description")
        if not isinstance(system_description, dict):
            return None
        return dict(system_description)

    @staticmethod
    def _dispatch_basic_analysis(
        file_type: PnmFileType,
        parser_model: object,
    ) -> BaseModel:
        if file_type == PnmFileType.RECEIVE_MODULATION_ERROR_RATIO:
            return Analysis.basic_analysis_rxmer_from_model(parser_model)
        if file_type == PnmFileType.OFDM_CHANNEL_ESTIMATE_COEFFICIENT:
            return Analysis.basic_analysis_ds_chan_est_from_model(parser_model)
        if file_type == PnmFileType.OFDM_MODULATION_PROFILE:
            return Analysis.basic_analysis_ds_modulation_profile_from_model(parser_model)
        if file_type == PnmFileType.DOWNSTREAM_CONSTELLATION_DISPLAY:
            return Analysis.basic_analysis_ds_constellation_display_from_model(parser_model)
        if file_type == PnmFileType.DOWNSTREAM_HISTOGRAM:
            return Analysis.basic_analysis_ds_histogram_from_model(parser_model)
        if file_type == PnmFileType.OFDM_FEC_SUMMARY:
            return Analysis.basic_analysis_ds_ofdm_fec_summary_from_model(parser_model)
        if file_type in (
            PnmFileType.UPSTREAM_PRE_EQUALIZER_COEFFICIENTS,
            PnmFileType.UPSTREAM_PRE_EQUALIZER_COEFFICIENTS_LAST_UPDATE,
        ):
            return Analysis.basic_analysis_us_ofdma_pre_equalization_from_model(parser_model)
        raise ValueError(f"Basic analysis not implemented for file type: {file_type.name}")

    @staticmethod
    def _dedupe_transaction_ids(
        transaction_ids: list[TransactionId],
    ) -> list[TransactionId]:
        seen: set[str] = set()
        unique: list[TransactionId] = []
        for transaction_id in transaction_ids:
            key = str(transaction_id)
            if key in seen:
                continue
            seen.add(key)
            unique.append(transaction_id)
        return unique


__all__ = [
    "PnmStoredCaptureAnalysisResultModel",
    "PnmStoredCaptureAnalysisService",
]

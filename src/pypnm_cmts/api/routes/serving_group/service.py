# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from datetime import datetime, timezone

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.lib.types import ChannelId, MacAddressStr

from pypnm_cmts.api.common.cmts_reg_status import CmtsCmRegStateModel
from pypnm_cmts.api.routes.serving_group.schemas import (
    GetServingGroupCableModemsRequest,
    GetServingGroupCableModemsResponse,
    GetServingGroupIdsResponse,
    GetServingGroupTopologyRequest,
    GetServingGroupTopologyResponse,
    ServingGroupCableModemEntryModel,
    ServingGroupCableModemsGroupModel,
    ServingGroupCacheSummaryModel,
    ServingGroupStatusResponse,
    ServingGroupTopologyChannelCountModel,
    ServingGroupTopologyChannelSetCountModel,
    ServingGroupTopologyChannelsModel,
    ServingGroupTopologyDownstreamChannelsModel,
    ServingGroupTopologyGroupModel,
    ServingGroupTopologyUpstreamChannelsModel,
)
from pypnm_cmts.docsis.data_type.cmts_cm_reg_state import decode_cmts_cm_reg_state
from pypnm_cmts.lib.constants import CacheRefreshMode, RfChannelType
from pypnm_cmts.lib.types import ChSetId, CmtsCmRegState, ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)
from pypnm_cmts.sgw.models import SgwCableModemModel, SgwRfChannelModel
from pypnm_cmts.sgw.runtime_state import (
    compute_sgw_cache_ready,
    get_sgw_manager,
    get_sgw_startup_status,
    get_sgw_store,
    is_sgw_refresh_running,
)
from pypnm_cmts.sgw.store import SgwCacheStore


class ServingGroupCacheService:
    """Service layer for cache-backed serving group endpoints."""

    STORE_UNAVAILABLE_MESSAGE = "sgw store not available"
    SNAPSHOT_MISSING_TEMPLATE = "sgw snapshot missing for sg_id={sg_id}"
    SG_NOT_FOUND_TEMPLATE = "sg_id not found: {sg_id}"
    NO_DISCOVERED_MESSAGE = "no discovered service groups"

    def get_ids(self) -> GetServingGroupIdsResponse:
        """Return discovered service group identifiers and cache summaries."""
        status = get_sgw_startup_status()
        discovered_sg_ids = list(status.discovered_sg_ids)
        store = get_sgw_store()
        sgw_ready, _missing = compute_sgw_cache_ready(discovered_sg_ids, store)
        summaries: list[ServingGroupCacheSummaryModel] = []
        now_epoch = self._now_epoch()
        for sg_id in discovered_sg_ids:
            metadata = self._resolve_metadata(sg_id, store, now_epoch)
            summaries.append(ServingGroupCacheSummaryModel(sg_id=sg_id, metadata=metadata))
        message = "" if sgw_ready else "sgw cache not ready"
        return GetServingGroupIdsResponse(
            status=ServiceStatusCode.SUCCESS,
            message=message,
            timestamp=self._utc_now(),
            discovered_sg_ids=discovered_sg_ids,
            sgw_ready=sgw_ready,
            summaries=summaries,
        )

    def get_status(self) -> ServingGroupStatusResponse:
        """Return SGW startup and cache readiness status."""
        status = get_sgw_startup_status()
        discovered_sg_ids = list(status.discovered_sg_ids)
        store = get_sgw_store()
        cache_ready, missing_sg_ids = compute_sgw_cache_ready(discovered_sg_ids, store)
        message = "" if cache_ready else "sgw cache not ready"
        return ServingGroupStatusResponse(
            status=ServiceStatusCode.SUCCESS,
            message=message,
            timestamp=self._utc_now(),
            startup_status=status,
            refresh_running=is_sgw_refresh_running(),
            discovered_count=len(discovered_sg_ids),
            cache_ready=cache_ready,
            missing_sg_ids=missing_sg_ids,
        )

    def get_cable_modems(
        self,
        request: GetServingGroupCableModemsRequest,
    ) -> GetServingGroupCableModemsResponse:
        """Return paged cable modem membership grouped by service group."""
        status = get_sgw_startup_status()
        if not bool(status.startup_completed):
            return self._build_cable_modems_failure("sgw startup not completed")
        if not bool(status.discovery_ok) or bool(status.prime_failed):
            message = status.error_message if status.error_message != "" else "sgw startup failed"
            return self._build_cable_modems_failure(message)

        store = get_sgw_store()
        if store is None:
            return self._build_cable_modems_failure(self.STORE_UNAVAILABLE_MESSAGE)

        discovered_sg_ids = list(status.discovered_sg_ids)
        requested_sg_ids = list(request.cmts.serving_group.id)
        if requested_sg_ids:
            resolved_sg_ids = [sg_id for sg_id in requested_sg_ids if sg_id in discovered_sg_ids]
            missing_sg_ids = [sg_id for sg_id in requested_sg_ids if sg_id not in discovered_sg_ids]
        else:
            resolved_sg_ids = list(discovered_sg_ids)
            missing_sg_ids = []

        if not resolved_sg_ids:
            message = self.NO_DISCOVERED_MESSAGE if not requested_sg_ids else self.SG_NOT_FOUND_TEMPLATE.format(
                sg_id=int(requested_sg_ids[0])
            )
            status_code = ServiceStatusCode.SUCCESS if not requested_sg_ids else ServiceStatusCode.FAILURE
            return GetServingGroupCableModemsResponse(
                status=status_code,
                message=message,
                timestamp=self._utc_now(),
                requested_sg_ids=requested_sg_ids,
                resolved_sg_ids=[],
                missing_sg_ids=list(requested_sg_ids),
                groups=[],
            )

        now_epoch = self._now_epoch()
        groups: list[ServingGroupCableModemsGroupModel] = []
        for sg_id in sorted(resolved_sg_ids, key=lambda value: int(value)):
            group = self._build_modem_group(
                sg_id=sg_id,
                store=store,
                now_epoch=now_epoch,
                page=request.page,
                page_size=request.page_size,
            )
            groups.append(group)
        return GetServingGroupCableModemsResponse(
            status=ServiceStatusCode.SUCCESS,
            message="" if groups else self.NO_DISCOVERED_MESSAGE,
            timestamp=self._utc_now(),
            requested_sg_ids=requested_sg_ids,
            resolved_sg_ids=sorted(resolved_sg_ids, key=lambda value: int(value)),
            missing_sg_ids=missing_sg_ids,
            groups=groups,
        )

    def get_topology(
        self,
        request: GetServingGroupTopologyRequest,
    ) -> GetServingGroupTopologyResponse:
        """Return cached topology summary for a service group."""
        status = get_sgw_startup_status()
        if not bool(status.startup_completed):
            return self._build_topology_failure("sgw startup not completed")
        if not bool(status.discovery_ok) or bool(status.prime_failed):
            message = status.error_message if status.error_message != "" else "sgw startup failed"
            return self._build_topology_failure(message)

        store = get_sgw_store()
        if store is None:
            return self._build_topology_failure(self.STORE_UNAVAILABLE_MESSAGE)

        discovered_sg_ids = list(status.discovered_sg_ids)
        requested_sg_ids = list(request.cmts.serving_group.id)
        if requested_sg_ids:
            resolved_sg_ids = [sg_id for sg_id in requested_sg_ids if sg_id in discovered_sg_ids]
            missing_sg_ids = [sg_id for sg_id in requested_sg_ids if sg_id not in discovered_sg_ids]
        else:
            resolved_sg_ids = list(discovered_sg_ids)
            missing_sg_ids = []

        if not resolved_sg_ids:
            message = self.NO_DISCOVERED_MESSAGE if not requested_sg_ids else self.SG_NOT_FOUND_TEMPLATE.format(
                sg_id=int(requested_sg_ids[0])
            )
            status_code = ServiceStatusCode.SUCCESS if not requested_sg_ids else ServiceStatusCode.FAILURE
            return GetServingGroupTopologyResponse(
                status=status_code,
                message=message,
                timestamp=self._utc_now(),
                requested_sg_ids=requested_sg_ids,
                resolved_sg_ids=[],
                missing_sg_ids=list(requested_sg_ids),
                groups=[],
            )

        now_epoch = self._now_epoch()
        groups: list[ServingGroupTopologyGroupModel] = []
        for sg_id in sorted(resolved_sg_ids, key=lambda value: int(value)):
            group = self._build_topology_group(
                sg_id=sg_id,
                store=store,
                now_epoch=now_epoch,
                page=request.page,
                page_size=request.page_size,
            )
            groups.append(group)
        return GetServingGroupTopologyResponse(
            status=ServiceStatusCode.SUCCESS,
            message="" if groups else self.NO_DISCOVERED_MESSAGE,
            timestamp=self._utc_now(),
            requested_sg_ids=requested_sg_ids,
            resolved_sg_ids=sorted(resolved_sg_ids, key=lambda value: int(value)),
            missing_sg_ids=missing_sg_ids,
            groups=groups,
        )

    def _build_cable_modems_failure(self, message: str) -> GetServingGroupCableModemsResponse:
        return GetServingGroupCableModemsResponse(
            status=ServiceStatusCode.FAILURE,
            message=message,
            timestamp=self._utc_now(),
            requested_sg_ids=[],
            resolved_sg_ids=[],
            missing_sg_ids=[],
            groups=[],
        )

    def _build_topology_failure(self, message: str) -> GetServingGroupTopologyResponse:
        return GetServingGroupTopologyResponse(
            status=ServiceStatusCode.FAILURE,
            message=message,
            timestamp=self._utc_now(),
            requested_sg_ids=[],
            resolved_sg_ids=[],
            missing_sg_ids=[],
            groups=[],
        )

    def _resolve_aggregate_metadata(
        self,
        discovered_sg_ids: list[ServiceGroupId],
        store: SgwCacheStore | None,
        now_epoch: float,
    ) -> tuple[SgwCacheMetadataModel, str]:
        if store is None:
            return (self._build_error_metadata(self.STORE_UNAVAILABLE_MESSAGE), self.STORE_UNAVAILABLE_MESSAGE)
        missing: list[ServiceGroupId] = []
        entries = []
        for sg_id in discovered_sg_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                missing.append(sg_id)
                continue
            entries.append(entry)
        if missing:
            message = self.SNAPSHOT_MISSING_TEMPLATE.format(sg_id=int(missing[0]))
            return (self._build_error_metadata(message), message)
        if not entries:
            return (self._build_error_metadata(self.NO_DISCOVERED_MESSAGE), self.NO_DISCOVERED_MESSAGE)
        newest = max(entries, key=lambda entry: float(entry.snapshot.metadata.snapshot_time_epoch))
        metadata = self._resolve_metadata(newest.sg_id, store, now_epoch)
        return (metadata, "")

    def _build_modem_group(
        self,
        sg_id: ServiceGroupId,
        store: SgwCacheStore,
        now_epoch: float,
        page: int,
        page_size: int,
    ) -> ServingGroupCableModemsGroupModel:
        entry = store.get_entry(sg_id)
        if entry is None:
            metadata = self._build_error_metadata(self.SNAPSHOT_MISSING_TEMPLATE.format(sg_id=int(sg_id)))
            return ServingGroupCableModemsGroupModel(
                sg_id=sg_id,
                page=page,
                page_size=page_size,
                total_items=0,
                total_pages=0,
                items=[],
                metadata=metadata,
            )
        metadata = self._resolve_metadata(sg_id, store, now_epoch)
        ordered = self._sort_modems(entry.snapshot.cable_modems)
        total_items = len(ordered)
        total_pages = self._total_pages(total_items, page_size)
        paged = self._paginate_modems(ordered, page, page_size)
        ds_channel_ids = self._resolve_channel_ids(
            entry.snapshot.ds_rf_channels,
            entry.snapshot.ds_channels.channel_ids,
        )
        us_channel_ids = self._resolve_channel_ids(
            entry.snapshot.us_rf_channels,
            entry.snapshot.us_channels.channel_ids,
        )
        items = [
            self._build_modem_entry(
                modem,
                ds_channel_ids,
                us_channel_ids,
            )
            for modem in paged
        ]
        return ServingGroupCableModemsGroupModel(
            sg_id=sg_id,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
            metadata=metadata,
        )

    def _build_topology_group(
        self,
        sg_id: ServiceGroupId,
        store: SgwCacheStore,
        now_epoch: float,
        page: int,
        page_size: int,
    ) -> ServingGroupTopologyGroupModel:
        entry = store.get_entry(sg_id)
        if entry is None:
            metadata = self._build_error_metadata(self.SNAPSHOT_MISSING_TEMPLATE.format(sg_id=int(sg_id)))
            return ServingGroupTopologyGroupModel(
                sg_id=sg_id,
                page=page,
                page_size=page_size,
                total_items=0,
                total_pages=0,
                modems=[],
                metadata=metadata,
            )
        metadata = self._resolve_metadata(sg_id, store, now_epoch)
        ordered = self._sort_modems(entry.snapshot.cable_modems)
        total_items = len(ordered)
        total_pages = self._total_pages(total_items, page_size)
        paged = self._paginate_modems(ordered, page, page_size)
        modems = [MacAddressStr(str(modem.mac)) for modem in paged]
        ds_channels = self._resolve_rf_channels(
            entry.snapshot.ds_rf_channels,
            entry.snapshot.ds_channels.channel_ids,
            RfChannelType.SC_QAM,
        )
        us_channels = self._resolve_rf_channels(
            entry.snapshot.us_rf_channels,
            entry.snapshot.us_channels.channel_ids,
            RfChannelType.SC_QAM,
        )
        ds_channel_set_counts = self._build_channel_set_counts(ordered, True)
        us_channel_set_counts = self._build_channel_set_counts(ordered, False)
        ds_channel_counts = self._build_channel_counts(ds_channels, entry.snapshot.ds_ch_set_id, ds_channel_set_counts)
        us_channel_counts = self._build_channel_counts(us_channels, entry.snapshot.us_ch_set_id, us_channel_set_counts)
        ds_sc_qam = self._filter_channels(ds_channels, RfChannelType.SC_QAM)
        ds_ofdm = self._filter_channels(ds_channels, RfChannelType.OFDM)
        us_sc_qam = self._filter_channels(us_channels, RfChannelType.SC_QAM)
        us_ofdma = self._filter_channels(us_channels, RfChannelType.OFDMA)
        channels = ServingGroupTopologyChannelsModel(
            ds=ServingGroupTopologyDownstreamChannelsModel(
                sc_qam=ds_sc_qam,
                ofdm=ds_ofdm,
                counts=ds_channel_counts,
                set_counts=ds_channel_set_counts,
            ),
            us=ServingGroupTopologyUpstreamChannelsModel(
                sc_qam=us_sc_qam,
                ofdma=us_ofdma,
                counts=us_channel_counts,
                set_counts=us_channel_set_counts,
            ),
        )
        return ServingGroupTopologyGroupModel(
            sg_id=sg_id,
            ds_ch_set_id=entry.snapshot.ds_ch_set_id,
            us_ch_set_id=entry.snapshot.us_ch_set_id,
            channels=channels,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            modems=modems,
            metadata=metadata,
        )

    def _request_refresh(
        self,
        sg_ids: list[ServiceGroupId],
        refresh: CacheRefreshMode,
        now_epoch: float,
    ) -> tuple[bool, str]:
        manager = get_sgw_manager()
        if manager is None or refresh == CacheRefreshMode.NONE:
            return (False, "")
        applied = False
        failure_reasons: list[str] = []
        seen: set[str] = set()
        for sg_id in sg_ids:
            accepted, reason = manager.request_refresh(sg_id, refresh, now_epoch)
            if accepted:
                applied = True
            if reason and reason not in seen and len(failure_reasons) < 3:
                seen.add(reason)
                failure_reasons.append(reason)
        failure_message = "; ".join(failure_reasons) if failure_reasons else ""
        return (applied, failure_message)

    def _wait_for_refresh(
        self,
        request: GetServingGroupTopologyRequest,
        sg_ids: list[ServiceGroupId],
        store: SgwCacheStore | None,
        refresh_applied: bool,
    ) -> float:
        if not refresh_applied:
            return 0.0
        return 0.0

    @staticmethod
    def _snapshot_baseline(
        sg_ids: list[ServiceGroupId],
        store: SgwCacheStore,
    ) -> dict[ServiceGroupId, float]:
        baseline: dict[ServiceGroupId, float] = {}
        for sg_id in sg_ids:
            entry = store.get_entry(sg_id)
            snapshot_epoch = 0.0
            if entry is not None:
                snapshot_epoch = float(entry.snapshot.metadata.snapshot_time_epoch)
            baseline[sg_id] = snapshot_epoch
        return baseline

    @staticmethod
    def _snapshot_advanced(
        sg_ids: list[ServiceGroupId],
        store: SgwCacheStore,
        baseline: dict[ServiceGroupId, float],
    ) -> bool:
        for sg_id in sg_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                continue
            snapshot_epoch = float(entry.snapshot.metadata.snapshot_time_epoch)
            if snapshot_epoch > float(baseline.get(sg_id, 0.0)) and snapshot_epoch > 0:
                return True
        return False

    @staticmethod
    def _all_snapshots_advanced(
        sg_ids: list[ServiceGroupId],
        store: SgwCacheStore,
        baseline: dict[ServiceGroupId, float],
    ) -> bool:
        for sg_id in sg_ids:
            entry = store.get_entry(sg_id)
            if entry is None:
                return False
            snapshot_epoch = float(entry.snapshot.metadata.snapshot_time_epoch)
            baseline_epoch = float(baseline.get(sg_id, 0.0))
            if snapshot_epoch <= baseline_epoch or snapshot_epoch <= 0:
                return False
        return True

    def _resolve_metadata(
        self,
        sg_id: ServiceGroupId,
        store: SgwCacheStore | None,
        now_epoch: float,
    ) -> SgwCacheMetadataModel:
        if store is None:
            return self._build_error_metadata(self.STORE_UNAVAILABLE_MESSAGE)
        entry = store.get_entry(sg_id)
        if entry is None:
            message = self.SNAPSHOT_MISSING_TEMPLATE.format(sg_id=int(sg_id))
            return self._build_error_metadata(message)
        metadata = entry.snapshot.metadata
        snapshot_epoch = float(metadata.snapshot_time_epoch)
        if snapshot_epoch <= 0:
            return metadata
        age_seconds = max(0.0, float(now_epoch) - snapshot_epoch)
        return metadata.model_copy(update={"age_seconds": age_seconds})

    @staticmethod
    def _sort_modems(modems: list[SgwCableModemModel]) -> list[SgwCableModemModel]:
        return sorted(modems, key=lambda modem: (str(modem.mac), str(modem.ipv4), str(modem.ipv6)))

    @staticmethod
    def _resolve_rf_channels(
        channels: list[SgwRfChannelModel],
        fallback_ids: list[int],
        default_type: RfChannelType,
    ) -> list[SgwRfChannelModel]:
        if channels:
            return sorted(
                channels,
                key=lambda entry: (int(entry.channel_id), str(entry.channel_type)),
            )
        return [
            SgwRfChannelModel(
                channel_id=int(channel_id),
                channel_type=default_type,
            )
            for channel_id in fallback_ids
            if int(channel_id) > 0
        ]

    @staticmethod
    def _build_channel_set_counts(
        modems: list[SgwCableModemModel],
        is_downstream: bool,
    ) -> list[ServingGroupTopologyChannelSetCountModel]:
        counts: dict[int, int] = {}
        for modem in modems:
            ch_set = modem.ds_channel_set if is_downstream else modem.us_channel_set
            ch_set_id = int(ch_set)
            if ch_set_id <= 0:
                continue
            counts[ch_set_id] = counts.get(ch_set_id, 0) + 1
        return [
            ServingGroupTopologyChannelSetCountModel(
                ch_set_id=ChSetId(ch_set_id),
                modem_count=counts[ch_set_id],
            )
            for ch_set_id in sorted(counts.keys())
        ]

    @staticmethod
    def _build_channel_counts(
        channels: list[SgwRfChannelModel],
        ch_set_id: ChSetId,
        ch_set_counts: list[ServingGroupTopologyChannelSetCountModel],
    ) -> list[ServingGroupTopologyChannelCountModel]:
        count_by_set = {
            int(entry.ch_set_id): int(entry.modem_count)
            for entry in ch_set_counts
        }
        modem_count = count_by_set.get(int(ch_set_id), 0)
        return [
            ServingGroupTopologyChannelCountModel(
                channel_id=int(channel.channel_id),
                modem_count=modem_count,
            )
            for channel in channels
        ]

    @staticmethod
    def _filter_channels(
        channels: list[SgwRfChannelModel],
        channel_type: RfChannelType,
    ) -> list[SgwRfChannelModel]:
        return [
            channel
            for channel in channels
            if channel.channel_type == channel_type
        ]

    def _build_modem_entry(
        self,
        modem: SgwCableModemModel,
        ds_channel_ids: list[ChannelId],
        us_channel_ids: list[ChannelId],
    ) -> ServingGroupCableModemEntryModel:
        ipv4_value = "" if modem.ipv4 is None else str(modem.ipv4)
        ipv6_value = "" if modem.ipv6 is None else str(modem.ipv6)
        reg_status_value = CmtsCmRegState(modem.registration_status)
        return ServingGroupCableModemEntryModel(
            mac_address=str(modem.mac),
            ipv4=ipv4_value,
            ipv6=ipv6_value,
            ds_channel_ids=list(ds_channel_ids),
            us_channel_ids=list(us_channel_ids),
            registration_status=CmtsCmRegStateModel(
                status=reg_status_value,
                text=decode_cmts_cm_reg_state(int(reg_status_value)),
            ),
        )

    @staticmethod
    def _resolve_channel_ids(
        channels: list[SgwRfChannelModel],
        fallback_ids: list[int],
    ) -> list[ChannelId]:
        if channels:
            ordered = sorted(channels, key=lambda entry: int(entry.channel_id))
            return [ChannelId(int(entry.channel_id)) for entry in ordered]
        return [ChannelId(int(channel_id)) for channel_id in fallback_ids if int(channel_id) > 0]

    def _paginate_modems(
        self,
        modems: list[SgwCableModemModel],
        page: int,
        page_size: int,
    ) -> list[SgwCableModemModel]:
        start = (int(page) - 1) * int(page_size)
        end = start + int(page_size)
        if start >= len(modems):
            return []
        return modems[start:end]

    @staticmethod
    def _total_pages(total_items: int, page_size: int) -> int:
        if total_items <= 0:
            return 0
        return (int(total_items) + int(page_size) - 1) // int(page_size)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _now_epoch() -> float:
        return datetime.now(timezone.utc).timestamp()

    @staticmethod
    def _build_error_metadata(message: str) -> SgwCacheMetadataModel:
        bounded = message[:SGW_LAST_ERROR_MAX_LENGTH]
        return SgwCacheMetadataModel(
            snapshot_time_epoch=0.0,
            refresh_state=SgwRefreshState.ERROR,
            last_error=bounded,
        )

    @staticmethod
    def _apply_metadata_error(
        metadata: SgwCacheMetadataModel,
        message: str,
    ) -> SgwCacheMetadataModel:
        bounded = message[:SGW_LAST_ERROR_MAX_LENGTH]
        return metadata.model_copy(
            update={
                "refresh_state": SgwRefreshState.ERROR,
                "last_error": bounded,
            }
        )


__all__ = [
    "ServingGroupCacheService",
]

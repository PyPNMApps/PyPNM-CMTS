# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia
from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from pypnm.lib.types import HostNameStr, SnmpReadCommunity, SnmpWriteCommunity

from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.cmts.inventory_discovery import CmtsInventoryDiscoveryService
from pypnm_cmts.config.orchestrator_config import (
    CmtsOrchestratorSettings,
    ServiceGroupDescriptor,
)
from pypnm_cmts.config.owner_id_resolver import OwnerIdResolver
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import (
    CoordinationTickResultModel,
    ServiceGroupLeaseConflictModel,
)
from pypnm_cmts.coordination.service_group_lease import FileServiceGroupLease
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    LeaderId,
    OrchestratorRunId,
    OwnerId,
    ServiceGroupId,
    TickIndex,
)
from pypnm_cmts.orchestrator.models import (
    OrchestratorRunResultModel,
    OrchestratorStatusModel,
    ServiceGroupInventoryModel,
    WorkResultModel,
)
from pypnm_cmts.orchestrator.runtime import CmtsOrchestratorRuntime
from pypnm_cmts.orchestrator.sg_shard_planner import ServiceGroupShardPlanner
from pypnm_cmts.orchestrator.work_runner import WorkRunner
from pypnm_cmts.types.orchestrator_types import OrchestratorMode

DEFAULT_STATE_DIR = ".data/coordination"
DEFAULT_ELECTION_PREFIX = "cmts"
DEFAULT_ELECTION_LABEL = "primary"
INVENTORY_SOURCE_CONFIG = "config"
INVENTORY_SOURCE_DISCOVERY = "discovery"
INVENTORY_SOURCE_WORKER = "worker"
DEFAULT_CONFLICT_REASON = "Lease not acquired."


class CmtsOrchestratorLauncher:
    """
    One-shot orchestrator launcher for Phase-3 skeleton execution.
    """

    def __init__(
        self,
        config_path: CoordinationPath | None,
        mode: OrchestratorMode,
        sg_id: ServiceGroupId | None,
        owner_id: OwnerId | None = None,
        target_service_groups: int | None = None,
        shard_mode: str | None = None,
        tick_interval_seconds: float | None = None,
        leader_ttl_seconds: int | None = None,
        lease_ttl_seconds: int | None = None,
        state_dir: CoordinationPath | None = None,
        election_name: CoordinationElectionName | None = None,
        adapter_hostname: HostNameStr | None = None,
        adapter_read_community: SnmpReadCommunity | None = None,
        adapter_write_community: SnmpWriteCommunity | None = None,
        adapter_port: int | None = None,
        state_dir_override: Path | None = None,
    ) -> None:
        """
        Initialize a one-shot orchestrator launcher.

        Args:
            config_path (CoordinationPath | None): Optional system.json path override.
            mode (OrchestratorMode): Execution mode (standalone, controller, worker).
            sg_id (ServiceGroupId | None): Optional service group identifier for worker mode.
            owner_id (OwnerId | None): Optional explicit owner id override.
            target_service_groups (int | None): Optional target service group override.
            shard_mode (str | None): Optional shard mode override.
            tick_interval_seconds (float | None): Optional tick interval override.
            leader_ttl_seconds (int | None): Optional leader TTL override.
            lease_ttl_seconds (int | None): Optional lease TTL override.
            state_dir (CoordinationPath | None): Optional coordination state directory override.
            election_name (CoordinationElectionName | None): Optional election name override.
            adapter_hostname (HostNameStr | None): Optional CMTS hostname override.
            adapter_read_community (SnmpReadCommunity | None): Optional SNMP read community override.
            adapter_write_community (SnmpWriteCommunity | None): Optional SNMP write community override.
            adapter_port (int | None): Optional SNMP port override.
            state_dir_override (Path | None): Optional state directory override (tests only).
        """
        self._config_path = config_path
        self._mode = mode
        self._sg_id = sg_id
        self._owner_id = owner_id
        self._target_service_groups = target_service_groups
        self._shard_mode = shard_mode
        self._tick_interval_seconds = tick_interval_seconds
        self._leader_ttl_seconds = leader_ttl_seconds
        self._lease_ttl_seconds = lease_ttl_seconds
        self._state_dir = state_dir
        self._election_name = election_name
        self._adapter_hostname = adapter_hostname
        self._adapter_read_community = adapter_read_community
        self._adapter_write_community = adapter_write_community
        self._adapter_port = adapter_port
        self._state_dir_override = state_dir_override
        self._runtime: CmtsOrchestratorRuntime | None = None
        self._runtime_lock = threading.Lock()

    def _load_settings(self) -> CmtsOrchestratorSettings:
        settings = CmtsOrchestratorSettings.from_system_config(
            config_path=self._config_path if self._config_path != "" else None
        )
        return self._apply_overrides(settings)

    def _build_identity(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[OwnerId, LeaderId, CoordinationElectionName]:
        owner_id = OwnerIdResolver.resolve(str(settings.owner_id), state_dir)
        leader_id = self._build_leader_id(owner_id)
        election_name = self._build_election_name(settings)
        return owner_id, leader_id, election_name

    def _build_inventory_and_plan(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        is_leader: bool,
    ) -> tuple[list[ServiceGroupId], str, list[ServiceGroupId], int, int]:
        if self._is_controller_enabled():
            service_groups, source = self._build_controller_service_groups(
                settings=settings,
                state_dir=state_dir,
                is_leader=is_leader,
            )
        else:
            service_groups, source = self._build_service_groups(settings, state_dir)

        desired_sg_ids = list(service_groups)
        worker_count = 0
        if self._is_controller_enabled():
            desired_sg_ids, worker_count = self._plan_controller_service_groups(
                settings=settings,
                service_groups=service_groups,
            )

        effective_target = self._effective_target_service_groups(
            settings=settings,
            inventory_count=len(service_groups),
        )
        if self._is_controller_enabled() and int(settings.target_service_groups) == 0:
            effective_target = len(desired_sg_ids)

        return service_groups, source, desired_sg_ids, worker_count, effective_target

    def _build_manager(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        election_name: CoordinationElectionName,
        leader_id: LeaderId,
        owner_id: OwnerId,
        effective_target: int,
    ) -> CoordinationManager:
        return CoordinationManager(
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=owner_id,
            leader_ttl_seconds=int(settings.leader_ttl_seconds),
            lease_ttl_seconds=int(settings.lease_ttl_seconds),
            target_service_groups=effective_target,
            shard_mode=settings.shard_mode,
            leader_enabled=self._is_controller_enabled(),
            leader_id_validator=self._leader_id_validator()
            if self._is_controller_enabled()
            else None,
        )

    def _is_controller_enabled(self) -> bool:
        return self._mode in (OrchestratorMode.CONTROLLER, OrchestratorMode.COMBINED)

    def _is_controller_mode(self) -> bool:
        return self._mode == OrchestratorMode.CONTROLLER

    def _is_combined_mode(self) -> bool:
        return self._mode == OrchestratorMode.COMBINED

    def _is_worker_enabled(self) -> bool:
        return self._mode in (OrchestratorMode.WORKER, OrchestratorMode.COMBINED)

    def _should_refresh_leader_inventory(self, settings: CmtsOrchestratorSettings) -> bool:
        if not self._is_controller_enabled():
            return False
        if self._should_discover(settings):
            hostname_value = str(settings.adapter.hostname).strip()
            if hostname_value == "":
                return False
        return True

    def run_once(self) -> OrchestratorRunResultModel:
        """
        Execute a single orchestration tick and return a structured result.

        Returns:
            OrchestratorRunResultModel: Structured result for one orchestration tick.
        """
        settings = self._load_settings()

        state_dir = self._resolve_state_dir()
        owner_id, leader_id, election_name = self._build_identity(settings, state_dir)

        service_groups, source, desired_sg_ids, worker_count, effective_target = self._build_inventory_and_plan(
            settings=settings,
            state_dir=state_dir,
            is_leader=False,
        )
        inventory = ServiceGroupInventoryModel(
            sg_ids=service_groups,
            count=len(service_groups),
            source=source,
        )

        manager = self._build_manager(
            settings=settings,
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=owner_id,
            effective_target=effective_target,
        )

        if self._is_controller_mode():
            tick_result = manager.tick_leader_only()
            leader_status = manager.leader_status()
            service_groups, source, desired_sg_ids, worker_count, effective_target = self._build_inventory_and_plan(
                settings=settings,
                state_dir=state_dir,
                is_leader=leader_status.is_leader,
            )
            inventory = ServiceGroupInventoryModel(
                sg_ids=service_groups,
                count=len(service_groups),
                source=source,
            )
        else:
            tick_target = service_groups
            tick_result = manager.tick(tick_target)
        tick_value = int(tick_result.tick_index)
        tick_index = TickIndex(tick_value if tick_value > 0 else 1)
        acquired_sg_ids = sorted(tick_result.acquired_sg_ids, key=int)
        coordination_status = manager.status()
        if self._is_controller_mode():
            held_sg_ids = []
        else:
            held_sg_ids = sorted(coordination_status.held_sg_ids, key=int)
        conflicts = self._build_conflicts(
            desired_sg_ids=desired_sg_ids,
            leased_sg_ids=held_sg_ids,
            state_dir=state_dir,
            election_name=election_name,
            owner_id=owner_id,
            lease_ttl_seconds=int(settings.lease_ttl_seconds),
        )
        tick_result = tick_result.model_copy(
            update={
                "enabled_sg_ids": sorted(service_groups, key=int),
                "desired_sg_ids": sorted(desired_sg_ids, key=int),
                "leased_sg_ids": sorted(held_sg_ids, key=int),
                "conflicts": conflicts,
                "worker_count": worker_count,
            }
        )
        work_sg_ids = self._select_work_sg_ids(
            acquired_sg_ids=acquired_sg_ids,
            held_sg_ids=held_sg_ids,
        )
        lease_held = self._is_worker_lease_held(held_sg_ids=held_sg_ids)
        run_id = self._build_run_id(acquired_sg_ids=work_sg_ids, tick_index=tick_index, lease_held=lease_held)
        work_results = self._run_worker_tests(
            settings=settings,
            state_dir=state_dir,
            tick_index=tick_index,
            acquired_sg_ids=work_sg_ids,
            lease_held=lease_held,
        )

        return OrchestratorRunResultModel(
            mode=self._mode,
            tick_index=tick_index,
            run_id=run_id,
            lease_held=lease_held,
            inventory=inventory,
            coordination_tick=tick_result,
            coordination_status=coordination_status,
            leader_status=manager.leader_status(),
            target_service_groups=effective_target,
            work_results=work_results,
        )

    def run_forever(
        self,
        on_tick: Callable[[OrchestratorRunResultModel], None] | None = None,
        max_ticks: int | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> list[CoordinationTickResultModel]:
        """
        Execute the orchestration runtime tick loop until stopped.

        Args:
            on_tick (Callable[[OrchestratorRunResultModel], None] | None): Optional per-tick callback.
            max_ticks (int | None): Optional maximum ticks to execute (tests only).
            sleeper (Callable[[float], None] | None): Optional sleep override (tests only).

        Returns:
            list[CoordinationTickResultModel]: Collected tick results when max_ticks is provided.
        """
        settings = self._load_settings()

        state_dir = self._resolve_state_dir()
        owner_id, leader_id, election_name = self._build_identity(settings, state_dir)

        service_groups, source, desired_sg_ids, worker_count, effective_target = self._build_inventory_and_plan(
            settings=settings,
            state_dir=state_dir,
            is_leader=False,
        )
        inventory = ServiceGroupInventoryModel(
            sg_ids=service_groups,
            count=len(service_groups),
            source=source,
        )

        manager = self._build_manager(
            settings=settings,
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=owner_id,
            effective_target=effective_target,
        )

        runtime = CmtsOrchestratorRuntime(
            settings=settings,
            manager=manager,
            service_groups=service_groups,
            mode=self._mode,
            sg_id=self._sg_id,
        )
        controller_inventory_source = source
        controller_inventory_initialized = False

        def _refresh_leader_inventory() -> None:
            nonlocal service_groups, inventory, desired_sg_ids, worker_count, effective_target, controller_inventory_source, controller_inventory_initialized
            service_groups, controller_inventory_source, desired_sg_ids, worker_count, effective_target = self._build_inventory_and_plan(
                settings=settings,
                state_dir=state_dir,
                is_leader=True,
            )
            inventory = ServiceGroupInventoryModel(
                sg_ids=service_groups,
                count=len(service_groups),
                source=controller_inventory_source,
            )
            runtime.set_service_groups(service_groups)
            controller_inventory_initialized = True

        def _emit_result(tick_index: int, tick_result: CoordinationTickResultModel) -> None:
            nonlocal service_groups, inventory, desired_sg_ids, worker_count, effective_target, controller_inventory_source, controller_inventory_initialized
            tick_value = TickIndex(int(tick_index))
            acquired_sg_ids = sorted(tick_result.acquired_sg_ids, key=int)
            coordination_status = manager.status()
            held_sg_ids = [] if self._is_controller_mode() else sorted(coordination_status.held_sg_ids, key=int)
            if (
                coordination_status.is_leader
                and not controller_inventory_initialized
                and self._should_refresh_leader_inventory(settings)
            ):
                _refresh_leader_inventory()
            if on_tick is None:
                return
            conflicts = self._build_conflicts(
                desired_sg_ids=desired_sg_ids,
                leased_sg_ids=held_sg_ids,
                state_dir=state_dir,
                election_name=election_name,
                owner_id=owner_id,
                lease_ttl_seconds=int(settings.lease_ttl_seconds),
            )
            tick_result = tick_result.model_copy(
                update={
                    "enabled_sg_ids": sorted(service_groups, key=int),
                    "desired_sg_ids": sorted(desired_sg_ids, key=int),
                    "leased_sg_ids": sorted(held_sg_ids, key=int),
                    "conflicts": conflicts,
                    "worker_count": worker_count,
                }
            )
            work_sg_ids = self._select_work_sg_ids(
                acquired_sg_ids=acquired_sg_ids,
                held_sg_ids=held_sg_ids,
            )
            lease_held = self._is_worker_lease_held(held_sg_ids=held_sg_ids)
            run_id = self._build_run_id(acquired_sg_ids=work_sg_ids, tick_index=tick_value, lease_held=lease_held)
            work_results = self._run_worker_tests(
                settings=settings,
                state_dir=state_dir,
                tick_index=tick_value,
                acquired_sg_ids=work_sg_ids,
                lease_held=lease_held,
            )
            result = OrchestratorRunResultModel(
                mode=self._mode,
                tick_index=tick_value,
                run_id=run_id,
                lease_held=lease_held,
                inventory=inventory,
                coordination_tick=tick_result,
                coordination_status=coordination_status,
                leader_status=manager.leader_status(),
                target_service_groups=effective_target,
                work_results=work_results,
            )
            on_tick(result)

        with self._runtime_lock:
            self._runtime = runtime
        try:
            return runtime.run_forever(
                max_ticks=max_ticks,
                sleeper=sleeper,
                on_tick_indexed=_emit_result,
            )
        finally:
            with self._runtime_lock:
                self._runtime = None

    def stop_runtime(self) -> None:
        """
        Request the runtime to stop if it is running.
        """
        with self._runtime_lock:
            runtime = self._runtime
        if runtime is not None:
            runtime.stop()

    def build_status_snapshot(self) -> OrchestratorStatusModel:
        """
        Build an orchestration status snapshot without executing a tick.

        Returns:
            OrchestratorStatusModel: Status snapshot including inventory and coordination status.
        """
        settings = self._load_settings()

        state_dir = self._resolve_state_dir()
        owner_id, leader_id, election_name = self._build_identity(settings, state_dir)

        service_groups, source, _desired_sg_ids, _worker_count, effective_target = self._build_inventory_and_plan(
            settings=settings,
            state_dir=state_dir,
            is_leader=False,
        )
        inventory = ServiceGroupInventoryModel(
            sg_ids=service_groups,
            count=len(service_groups),
            source=source,
        )

        manager = self._build_manager(
            settings=settings,
            state_dir=state_dir,
            election_name=election_name,
            leader_id=leader_id,
            owner_id=owner_id,
            effective_target=effective_target,
        )

        return OrchestratorStatusModel(
            mode=self._mode,
            inventory=inventory,
            coordination_status=manager.status(),
            leader_status=manager.leader_status(),
            target_service_groups=effective_target,
        )

    def _resolve_state_dir(self) -> Path:
        if self._state_dir_override is not None:
            state_dir = self._state_dir_override
        elif self._state_dir is not None and str(self._state_dir).strip() != "":
            state_dir = Path(self._state_dir)
        else:
            state_dir = Path(DEFAULT_STATE_DIR)
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def _build_election_name(self, settings: CmtsOrchestratorSettings) -> CoordinationElectionName:
        if str(settings.election_name).strip() != "":
            return CoordinationElectionName(str(settings.election_name).strip())
        label = settings.adapter.label.strip() if settings.adapter.label.strip() != "" else DEFAULT_ELECTION_LABEL
        value = f"{DEFAULT_ELECTION_PREFIX}-{label}"
        return CoordinationElectionName(value)

    def _build_leader_id(self, owner_id: OwnerId) -> LeaderId:
        owner_value = str(owner_id).strip()
        if owner_value == "":
            owner_value = str(owner_id)
        if self._is_controller_enabled():
            if owner_value.startswith("controller-"):
                return LeaderId(owner_value)
            if owner_value.startswith("worker-"):
                stripped = owner_value[len("worker-") :]
                if stripped == "":
                    stripped = str(owner_id).strip()
                return LeaderId(f"controller-{stripped}")
            return LeaderId(f"controller-{owner_value}")
        if owner_value.startswith("worker-"):
            return LeaderId(owner_value)
        if owner_value.startswith("controller-"):
            stripped = owner_value[len("controller-") :]
            if stripped == "":
                stripped = str(owner_id).strip()
            return LeaderId(f"worker-{stripped}")
        return LeaderId(f"worker-{owner_value}")

    @staticmethod
    def _leader_id_validator() -> Callable[[LeaderId], bool]:
        def _is_controller(leader_id: LeaderId) -> bool:
            value = str(leader_id).strip()
            return value != "" and not value.startswith("worker-")

        return _is_controller

    def _build_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        if self._mode == OrchestratorMode.WORKER:
            return self._build_worker_service_groups(settings, state_dir)
        return self._build_inventory_service_groups(settings, state_dir)

    def _build_worker_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        if self._sg_id is None:
            snapshot = self._load_inventory_snapshot(state_dir)
            if snapshot is not None:
                return (sorted(snapshot.discovered_sg_ids, key=int), INVENTORY_SOURCE_DISCOVERY)
            if settings.service_groups:
                return self._build_config_service_groups(settings)
            if self._should_discover(settings):
                raise ValueError("inventory snapshot not found for worker mode.")
            return ([], INVENTORY_SOURCE_WORKER)

        config_groups = self._build_config_service_groups(settings)[0]
        if settings.service_groups:
            if self._sg_id not in config_groups:
                raise ValueError("worker sg-id is not enabled in configuration.")
            return ([self._sg_id], INVENTORY_SOURCE_CONFIG)

        return ([self._sg_id], INVENTORY_SOURCE_WORKER)

    def _build_inventory_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        if bool(settings.auto_discover):
            return self._build_discovered_service_groups(settings, state_dir)
        return self._build_config_service_groups(settings)

    def _build_controller_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        is_leader: bool,
    ) -> tuple[list[ServiceGroupId], str]:
        if is_leader and self._should_discover(settings):
            hostname_value = str(settings.adapter.hostname).strip()
            if hostname_value != "":
                return self._build_discovered_service_groups(settings, state_dir)

        snapshot = self._load_inventory_snapshot(state_dir)
        if snapshot is not None:
            return (sorted(snapshot.discovered_sg_ids, key=int), INVENTORY_SOURCE_DISCOVERY)

        service_groups, source = self._build_config_service_groups(settings)
        if is_leader and service_groups:
            self._persist_inventory_snapshot(settings, state_dir, service_groups)
        return (service_groups, source)

    def _build_discovered_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
    ) -> tuple[list[ServiceGroupId], str]:
        result = CmtsInventoryDiscoveryService.run_discovery(
            cmts_hostname=settings.adapter.hostname,
            read_community=settings.adapter.community,
            write_community=settings.adapter.write_community,
            port=int(settings.adapter.port),
            state_dir=state_dir,
        )
        return (sorted(result.discovered_sg_ids, key=int), INVENTORY_SOURCE_DISCOVERY)

    def _load_inventory_snapshot(self, state_dir: Path) -> InventoryDiscoveryResultModel | None:
        snapshot_path = state_dir / "inventory" / "discovery.json"
        if not snapshot_path.exists():
            return None
        try:
            content = snapshot_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise ValueError("inventory snapshot could not be read.") from exc
        try:
            return InventoryDiscoveryResultModel.model_validate_json(content)
        except Exception as exc:
            raise ValueError("inventory snapshot is invalid.") from exc

    def _persist_inventory_snapshot(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        sg_ids: list[ServiceGroupId],
    ) -> None:
        snapshot = InventoryDiscoveryResultModel(
            cmts_host=HostNameStr(str(settings.adapter.hostname)),
            discovered_sg_ids=sorted(sg_ids, key=int),
            per_sg=[],
        )
        inventory_dir = state_dir / "inventory"
        inventory_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = inventory_dir / "discovery.json"
        snapshot_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

    def _build_config_service_groups(self, settings: CmtsOrchestratorSettings) -> tuple[list[ServiceGroupId], str]:
        enabled_ids: list[ServiceGroupId] = []
        for entry in settings.service_groups:
            if not entry.enabled:
                continue
            enabled_ids.append(entry.sg_id)
        return (sorted(enabled_ids, key=int), INVENTORY_SOURCE_CONFIG)

    def _plan_controller_service_groups(
        self,
        settings: CmtsOrchestratorSettings,
        service_groups: list[ServiceGroupId],
    ) -> tuple[list[ServiceGroupId], int]:
        descriptors = self._build_planner_descriptors(settings, service_groups)
        return ServiceGroupShardPlanner.plan(
            descriptors=descriptors,
            shard_mode=settings.shard_mode,
            target_service_groups=int(settings.target_service_groups),
            worker_cap=int(settings.worker_cap),
        )

    def _build_planner_descriptors(
        self,
        settings: CmtsOrchestratorSettings,
        service_groups: list[ServiceGroupId],
    ) -> list[ServiceGroupDescriptor]:
        if settings.service_groups:
            return list(settings.service_groups)
        return [ServiceGroupDescriptor(sg_id=sg_id) for sg_id in service_groups]

    def _effective_target_service_groups(self, settings: CmtsOrchestratorSettings, inventory_count: int) -> int:
        if self._is_worker_enabled() and self._sg_id is not None:
            requested = 1
        else:
            requested = int(settings.target_service_groups)
        if inventory_count <= 0:
            return 0
        return min(requested, inventory_count)

    def _run_worker_tests(
        self,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        tick_index: TickIndex,
        acquired_sg_ids: list[ServiceGroupId],
        lease_held: bool,
    ) -> list[WorkResultModel]:
        if not self._is_worker_enabled():
            return []
        if not lease_held:
            return []
        if not acquired_sg_ids:
            return []

        tests = [str(test_name) for test_name in settings.default_tests]
        runner = WorkRunner(state_dir=state_dir)
        sg_id = sorted(acquired_sg_ids, key=int)[0]
        run_id = self._build_run_id_for_sg(sg_id=sg_id, tick_index=tick_index)
        return runner.run_tests(sg_id=sg_id, tests=tests, run_id=run_id)

    def _build_run_id(
        self,
        acquired_sg_ids: list[ServiceGroupId],
        tick_index: TickIndex,
        lease_held: bool,
    ) -> OrchestratorRunId:
        if not self._is_worker_enabled():
            return OrchestratorRunId("")
        if not lease_held:
            return OrchestratorRunId("")
        if not acquired_sg_ids:
            return OrchestratorRunId("")
        sg_id = sorted(acquired_sg_ids, key=int)[0]
        return self._build_run_id_for_sg(sg_id=sg_id, tick_index=tick_index)

    def _build_run_id_for_sg(
        self,
        sg_id: ServiceGroupId,
        tick_index: TickIndex,
    ) -> OrchestratorRunId:
        value = f"sg{int(sg_id)}_tick{int(tick_index):06d}"
        return OrchestratorRunId(value)

    def _build_conflicts(
        self,
        desired_sg_ids: list[ServiceGroupId],
        leased_sg_ids: list[ServiceGroupId],
        state_dir: Path,
        election_name: CoordinationElectionName,
        owner_id: OwnerId,
        lease_ttl_seconds: int,
    ) -> list[ServiceGroupLeaseConflictModel]:
        if not desired_sg_ids:
            return []

        conflicts: list[ServiceGroupLeaseConflictModel] = []
        for sg_id in sorted(desired_sg_ids, key=int):
            if sg_id in leased_sg_ids:
                continue
            lease = FileServiceGroupLease(
                state_dir=state_dir,
                election_name=election_name,
                sg_id=sg_id,
                owner_id=owner_id,
                ttl_seconds=int(lease_ttl_seconds),
            )
            status = lease.status()
            reason = status.message if status.message != "" else DEFAULT_CONFLICT_REASON
            conflicts.append(
                ServiceGroupLeaseConflictModel(
                    sg_id=sg_id,
                    owner_id=status.owner_id,
                    reason=reason,
                )
            )
        return conflicts

    def _select_work_sg_ids(
        self,
        acquired_sg_ids: list[ServiceGroupId],
        held_sg_ids: list[ServiceGroupId],
    ) -> list[ServiceGroupId]:
        if acquired_sg_ids:
            return sorted(acquired_sg_ids, key=int)[:1]
        return sorted(held_sg_ids, key=int)[:1]

    def _is_worker_lease_held(self, held_sg_ids: list[ServiceGroupId]) -> bool:
        if not self._is_worker_enabled():
            return False
        return bool(held_sg_ids)

    def _should_discover(self, settings: CmtsOrchestratorSettings) -> bool:
        return bool(settings.auto_discover)

    def _apply_overrides(self, settings: CmtsOrchestratorSettings) -> CmtsOrchestratorSettings:
        data = settings.model_dump()
        adapter_data = dict(data.get("adapter", {}))

        if self._owner_id is not None and str(self._owner_id).strip() != "":
            data["owner_id"] = str(self._owner_id)
        if self._target_service_groups is not None:
            data["target_service_groups"] = int(self._target_service_groups)
        if self._shard_mode is not None and self._shard_mode.strip() != "":
            data["shard_mode"] = self._shard_mode
        if self._tick_interval_seconds is not None:
            data["tick_interval_seconds"] = float(self._tick_interval_seconds)
        if self._leader_ttl_seconds is not None:
            data["leader_ttl_seconds"] = int(self._leader_ttl_seconds)
        if self._lease_ttl_seconds is not None:
            data["lease_ttl_seconds"] = int(self._lease_ttl_seconds)
        if self._state_dir is not None and str(self._state_dir).strip() != "":
            data["state_dir"] = str(self._state_dir)
        if self._election_name is not None:
            election_value = str(self._election_name).strip()
            data["election_name"] = election_value
        if self._adapter_hostname is not None and str(self._adapter_hostname).strip() != "":
            adapter_data["hostname"] = str(self._adapter_hostname)
        if self._adapter_read_community is not None and str(self._adapter_read_community).strip() != "":
            adapter_data["community"] = str(self._adapter_read_community)
        if self._adapter_write_community is not None and str(self._adapter_write_community).strip() != "":
            adapter_data["write_community"] = str(self._adapter_write_community)
        if self._adapter_port is not None:
            adapter_data["port"] = int(self._adapter_port)

        data["adapter"] = adapter_data

        return CmtsOrchestratorSettings.model_validate(data)

    @staticmethod
    def _parse_sg_id(value: str) -> ServiceGroupId:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("service group id must be non-empty.")
        try:
            return ServiceGroupId(int(trimmed))
        except ValueError as exc:
            raise ValueError("service group id must be a numeric value.") from exc


__all__ = [
    "CmtsOrchestratorLauncher",
    "DEFAULT_STATE_DIR",
]

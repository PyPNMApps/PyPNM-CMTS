# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypnm.docsis.data_type.sysDescr import SystemDescriptorModel

from pypnm_cmts.config.orchestrator_config import (
    CmtsOrchestratorSettings,
    ServiceGroupDescriptor,
)
from pypnm_cmts.lib.constants import OperationalStatus, ReadinessCheck
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import (
    SgwCableModemModel,
    SgwCacheEntryModel,
    SgwSnapshotModel,
)
from pypnm_cmts.sgw.runtime_state import (
    reset_sgw_runtime_state,
    set_sgw_startup_success,
)
from pypnm_cmts.sgw.store import SgwCacheStore
from pypnm_cmts.types.orchestrator_types import OrchestratorMode
from pypnm_cmts.version import __version__


def _load_app(settings: CmtsOrchestratorSettings, monkeypatch: object) -> FastAPI:
    from pypnm_cmts.api.routes.operational.router import router as operational_router

    app = FastAPI(title="PyPNM-CMTS Operational API", version=__version__)
    app.include_router(operational_router)

    def _fake_from_system_config(**_kwargs: object) -> CmtsOrchestratorSettings:
        return settings

    monkeypatch.setattr(
        CmtsOrchestratorSettings,
        "from_system_config",
        classmethod(lambda cls, **_kwargs: _fake_from_system_config()),
    )
    return app


def _client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _build_settings(
    mode: OrchestratorMode,
    state_dir: Path,
    service_groups: list[ServiceGroupDescriptor],
    election_name: str | None = None,
) -> CmtsOrchestratorSettings:
    payload = {
        "mode": mode,
        "state_dir": str(state_dir),
        "service_groups": [entry.model_dump() for entry in service_groups],
        "default_tests": ["test-a"],
        "adapter": {"hostname": "cmts.example", "community": "public"},
    }
    if election_name is not None:
        payload["election_name"] = election_name
    return CmtsOrchestratorSettings.model_validate(payload)


def _mark_sgw_ready(settings: CmtsOrchestratorSettings) -> None:
    now_epoch = 0.0
    reset_sgw_runtime_state()
    store = SgwCacheStore()
    manager = SgwManager(settings=settings, store=store, service_groups=[])
    set_sgw_startup_success([], store, manager, now_epoch)


def _set_sgw_runtime(
    settings: CmtsOrchestratorSettings,
    service_groups: list[ServiceGroupId],
    now_epoch: float,
) -> SgwManager:
    reset_sgw_runtime_state()
    store = SgwCacheStore()
    manager = SgwManager(settings=settings, store=store, service_groups=service_groups)
    set_sgw_startup_success(service_groups, store, manager, now_epoch)
    return manager


def test_ops_health_returns_ok(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "state"
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        [],
        election_name="ops-demo",
    )
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["timestamp"] != ""
    assert payload["meta"]["mode"] == OrchestratorMode.STANDALONE.value
    assert payload["meta"]["state_dir"] == str(state_dir)
    assert payload["meta"]["election_name"] == "ops-demo"


def test_ops_version_returns_metadata(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "state"
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        [],
        election_name="ops-version",
    )
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["application"] == "pypnm-cmts"
    assert payload["version"] == __version__
    assert payload["python_version"] != ""
    assert payload["timestamp"] != ""
    assert payload["meta"]["state_dir"] == str(state_dir)
    assert payload["meta"]["election_name"] == "ops-version"


def test_ops_ready_controller_creates_state_dir(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    _mark_sgw_ready(settings)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert state_dir.exists()
    assert (state_dir / "pids").exists()
    assert (state_dir / "logs").exists()
    assert (state_dir / "inventory").exists()


def test_ops_ready_controller_not_writable(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    _mark_sgw_ready(settings)
    app = _load_app(settings, monkeypatch)
    from pypnm_cmts.api.routes.operational.service import OperationalService

    monkeypatch.setattr(OperationalService, "_ensure_state_dir_writable", lambda *_args: False)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["failed_check"] == ReadinessCheck.STATE_DIR_ACCESS.value
    assert body["status"] == OperationalStatus.ERROR.value


def test_ops_ready_worker_requires_sg(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    state_dir.mkdir(parents=True, exist_ok=True)
    settings = _build_settings(OrchestratorMode.WORKER, state_dir, [])
    _mark_sgw_ready(settings)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["failed_check"] == ReadinessCheck.WORKER_SG.value


def test_ops_ready_worker_ok(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    state_dir.mkdir(parents=True, exist_ok=True)
    service_groups = [ServiceGroupDescriptor(sg_id=1, name="sg-1", enabled=True)]
    settings = _build_settings(OrchestratorMode.WORKER, state_dir, service_groups)
    _mark_sgw_ready(settings)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["meta"]["sg_id"] == service_groups[0].sg_id


def test_ops_ready_rejects_blank_state_dir(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.STANDALONE, state_dir, [])
    _mark_sgw_ready(settings)
    blank_settings = settings.model_copy(update={"state_dir": "   "})
    app = _load_app(blank_settings, monkeypatch)
    from pypnm_cmts.api.routes.operational.service import OperationalService

    def _fail_if_called(_self: OperationalService, _path: Path) -> bool:
        raise AssertionError("state_dir check should fail before directory creation")

    monkeypatch.setattr(OperationalService, "_ensure_state_dir_exists", _fail_if_called)

    client = _client(app)
    response = client.get("/ops/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["failed_check"] == ReadinessCheck.STATE_DIR.value


def test_ops_status_missing_pid_records(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.ERROR.value
    assert payload["pid_records_missing"] is True
    assert payload["pid_records_stale"] is False
    assert payload["fallback_used"] is False


def test_ops_status_pidfile_parsing(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    pid_dir = state_dir / "pids"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "controller.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_5.pid").write_text("999999", encoding="utf-8")
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pid_records_missing"] is False
    assert payload["pid_records_stale"] is True
    assert payload["status"] == OperationalStatus.ERROR.value
    assert payload["controller"]["pidfile_exists"] is True
    assert payload["controller"]["pid"] == 999999
    assert payload["controller"]["is_running"] is False
    assert payload["workers"][0]["pidfile_exists"] is True
    assert payload["workers"][0]["pid"] == 999999
    assert payload["workers"][0]["is_running"] is False
    assert payload["workers"][0]["sg_id"] == 5


def test_ops_status_skips_fallback_without_election(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(
        OrchestratorMode.CONTROLLER,
        state_dir,
        [],
        election_name=None,
    )
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is False


def test_ops_memory_detail_reports_sgw_and_operation_stats(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(OrchestratorMode.STANDALONE, state_dir, [])
    reset_sgw_runtime_state()
    store = SgwCacheStore()
    entry = SgwCacheEntryModel(
        sg_id=ServiceGroupId(1),
        snapshot=SgwSnapshotModel(
            sg_id=ServiceGroupId(1),
            cable_modems=[
                SgwCableModemModel(
                    mac="00:11:22:33:44:55",
                    ipv4="192.0.2.10",
                    sysdescr=SystemDescriptorModel(sysDescr="Docsis Modem"),
                )
            ],
        ),
    )
    store.upsert_entry(entry)
    manager = SgwManager(settings=settings, store=store, service_groups=[ServiceGroupId(1)])
    set_sgw_startup_success([ServiceGroupId(1)], store, manager, 0.0)

    operations_dir = tmp_path / "sg_operations" / "op-1" / "results"
    operations_dir.mkdir(parents=True, exist_ok=True)
    (operations_dir.parent / "state.json").write_text("{}", encoding="utf-8")
    (operations_dir / "sg-1.jsonl").write_text("{\"ok\":true}\n", encoding="utf-8")

    app = _load_app(settings, monkeypatch)
    from pypnm_cmts.api.common.service.pnm.operation_service import (
        PnmServiceGroupOperationServiceBase,
    )
    from pypnm_cmts.api.routes.operational.service import OperationalService

    monkeypatch.setattr(OperationalService, "_operation_store_base_dir", staticmethod(lambda: tmp_path / "sg_operations"))
    monkeypatch.setattr(
        PnmServiceGroupOperationServiceBase,
        "get_registered_services",
        classmethod(
            lambda cls: [
                _FakePnmService(
                    {
                        "service_name": "FakePnmService",
                        "thread_count": 1,
                        "alive_thread_count": 1,
                        "tracked_operation_count": 1,
                        "total_pending_futures": 2,
                        "total_abandoned_futures": 3,
                        "total_retry_queue_items": 4,
                        "total_queue_items": 5,
                    }
                )
            ]
        ),
    )
    client = _client(app)
    response = client.get("/ops/health/memoryDetail")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["sgw_cache"]["service_group_count"] == 1
    assert payload["sgw_cache"]["modem_count"] == 1
    assert payload["sgw_cache"]["sysdescr_count"] == 1
    assert payload["operations"]["operation_dir_count"] == 1
    assert payload["operations"]["state_file_count"] == 1
    assert payload["operations"]["result_file_count"] == 1
    assert payload["pnm_runners"][0]["service_name"] == "FakePnmService"
    assert payload["pnm_runners"][0]["total_abandoned_futures"] == 3


class _FakePnmService:
    def __init__(self, stats: dict[str, int | str]) -> None:
        self._stats = stats

    def get_debug_stats(self) -> dict[str, int | str]:
        return self._stats


def test_ops_status_worker_sorting(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    pid_dir = state_dir / "pids"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "controller.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_10.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_2.pid").write_text("999999", encoding="utf-8")
    (pid_dir / "worker_unbound.pid").write_text("999999", encoding="utf-8")
    settings = _build_settings(OrchestratorMode.CONTROLLER, state_dir, [])
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    workers = payload["workers"]
    assert workers[0]["sg_id"] == 2
    assert workers[1]["sg_id"] == 10
    assert workers[2]["sg_id"] is None


def test_ops_status_fallback_arg_equals_parsing(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(
        OrchestratorMode.CONTROLLER,
        state_dir,
        [],
        election_name="ops-demo",
    )
    app = _load_app(settings, monkeypatch)
    from pypnm_cmts.api.routes.operational.service import OperationalService

    def _fake_fallback(_self: OperationalService, _election: str) -> list[tuple[int, str]]:
        return [
            (
                999999,
                "pypnm-cmts run-forever --election-name=ops-demo --mode=worker --sg-id=7",
            )
        ]

    monkeypatch.setattr(OperationalService, "_fallback_find_processes", _fake_fallback)

    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is True
    workers = payload["workers"]
    assert len(workers) == 1
    assert workers[0]["sg_id"] == 7
    assert workers[0]["pidfile_exists"] is False


def test_ops_status_fallback_combined_mode_signature(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(
        OrchestratorMode.CONTROLLER,
        state_dir,
        [],
        election_name="ops-combined",
    )
    app = _load_app(settings, monkeypatch)
    from pypnm_cmts.api.routes.operational.service import OperationalService

    def _fake_fallback(_self: OperationalService, _election: str) -> list[tuple[int, str]]:
        return [
            (
                555555,
                "pypnm-cmts serve --with-runner --election-name=ops-combined",
            )
        ]

    monkeypatch.setattr(OperationalService, "_fallback_find_processes", _fake_fallback)

    client = _client(app)
    response = client.get("/ops/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is True
    workers = payload["workers"]
    assert len(workers) == 1
    assert workers[0]["pid"] == 555555
    assert workers[0]["sg_id"] is None


def test_ops_sgw_process_reports_workers(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    service_groups = [
        ServiceGroupDescriptor(sg_id=1, name="sg-1", enabled=True),
        ServiceGroupDescriptor(sg_id=2, name="sg-2", enabled=True),
    ]
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        service_groups,
        election_name="ops-sgw",
    )
    monkeypatch.setattr("pypnm_cmts.sgw.manager.time.time", lambda: 100.0)
    _set_sgw_runtime(settings, [ServiceGroupId(1), ServiceGroupId(2)], now_epoch=100.0)
    monkeypatch.setattr("pypnm_cmts.api.routes.operational.service.time.time", lambda: 160.0)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/servingGroupWorker/process")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    workers = payload["workers"]
    assert [entry["worker_id"] for entry in workers] == ["sgw-1", "sgw-2"]
    assert [entry["sg_id"] for entry in workers] == [1, 2]
    reset_sgw_runtime_state()


def test_ops_sgw_poll_interval_reports_counts(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    service_groups = [ServiceGroupDescriptor(sg_id=1, name="sg-1", enabled=True)]
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        service_groups,
        election_name="ops-sgw",
    )
    manager = _set_sgw_runtime(settings, [ServiceGroupId(1)], now_epoch=100.0)
    manager.refresh_once(100.0)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/servingGroupWorker/poll-interval")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    workers = payload["workers"]
    assert len(workers) == 1
    assert workers[0]["heavy_interval_seconds"] == int(settings.sgw.poll_heavy_seconds)
    assert workers[0]["light_interval_seconds"] == int(settings.sgw.poll_light_seconds)
    assert workers[0]["heavy_count"] == 1
    assert workers[0]["light_count"] == 1
    reset_sgw_runtime_state()


def test_ops_sgw_restart_queues_refresh(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    service_groups = [ServiceGroupDescriptor(sg_id=1, name="sg-1", enabled=True)]
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        service_groups,
        election_name="ops-sgw",
    )
    manager = _set_sgw_runtime(settings, [ServiceGroupId(1)], now_epoch=100.0)
    captured: dict[str, object] = {}

    def _fake_request_refresh(
        sg_id: ServiceGroupId,
        mode: object,
        now_epoch: float,
    ) -> tuple[bool, str]:
        captured["sg_id"] = sg_id
        captured["mode"] = mode
        captured["now_epoch"] = now_epoch
        return (True, "")

    monkeypatch.setattr(manager, "request_refresh", _fake_request_refresh)
    monkeypatch.setattr("pypnm_cmts.api.routes.operational.service.time.time", lambda: 160.0)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.post("/ops/servingGroupWorker/restart", json={"worker_id": "sgw-1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    assert payload["sg_id"] == 1
    assert "queued heavy refresh for sgw-1" in payload["message"]
    assert captured["sg_id"] == ServiceGroupId(1)
    reset_sgw_runtime_state()


def test_ops_sgw_process_requires_manager(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        [],
        election_name="ops-sgw",
    )
    reset_sgw_runtime_state()
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.get("/ops/servingGroupWorker/process")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == OperationalStatus.ERROR.value


def test_ops_sgw_reset_clears_counts(tmp_path: Path, monkeypatch: object) -> None:
    state_dir = tmp_path / "coordination"
    service_groups = [ServiceGroupDescriptor(sg_id=1, name="sg-1", enabled=True)]
    settings = _build_settings(
        OrchestratorMode.STANDALONE,
        state_dir,
        service_groups,
        election_name="ops-sgw",
    )
    manager = _set_sgw_runtime(settings, [ServiceGroupId(1)], now_epoch=100.0)
    manager.refresh_once(100.0)
    app = _load_app(settings, monkeypatch)
    client = _client(app)
    response = client.post("/ops/servingGroupWorker/resetCounters", json={"worker_id": "sgw-1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == OperationalStatus.OK.value
    response = client.get("/ops/servingGroupWorker/poll-interval")
    assert response.status_code == 200
    poll_payload = response.json()
    workers = poll_payload["workers"]
    assert workers[0]["heavy_count"] == 0
    assert workers[0]["light_count"] == 0
    reset_sgw_runtime_state()

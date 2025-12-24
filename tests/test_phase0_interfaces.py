# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import inspect

from pypnm_cmts.cmts.adapters.base import CmtsAdapter
from pypnm_cmts.coordination.interfaces import LeaderElection, ServiceGroupLease
from pypnm_cmts.launcher.interfaces import WorkerLauncher


def test_cmts_adapter_is_abstract() -> None:
    assert inspect.isabstract(CmtsAdapter)


def test_worker_launcher_is_abstract() -> None:
    assert inspect.isabstract(WorkerLauncher)


def test_leader_election_is_abstract() -> None:
    assert inspect.isabstract(LeaderElection)


def test_service_group_lease_is_abstract() -> None:
    assert inspect.isabstract(ServiceGroupLease)

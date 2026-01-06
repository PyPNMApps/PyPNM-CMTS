# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm.snmp.compiled_oids import COMPILED_OIDS

MIN_OID_COUNT = 1
SYS_DESCR_KEY = "sysDescr"
OID_PREFIXES = ("1.", ".1.")


def test_compiled_oids_accessible() -> None:
    assert isinstance(COMPILED_OIDS, dict)

    oid_count = len(COMPILED_OIDS)
    assert oid_count >= MIN_OID_COUNT, f"Expected at least {MIN_OID_COUNT} OID entries, got {oid_count}"

    assert SYS_DESCR_KEY in COMPILED_OIDS, f"Expected {SYS_DESCR_KEY} in COMPILED_OIDS"

    sys_descr_oid = COMPILED_OIDS[SYS_DESCR_KEY]
    assert isinstance(sys_descr_oid, str)
    assert sys_descr_oid.startswith(OID_PREFIXES)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

"""PNM orchestration router."""
from __future__ import annotations

from fastapi import APIRouter

from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.channel_est_coeff.router import (
    router as channel_est_coeff_router,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.const_display.router import (
    router as const_display_router,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.fec_summary.router import (
    router as fec_summary_router,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.modulation_profile.router import (
    router as modulation_profile_router,
)
from pypnm_cmts.api.routes.pnm.sg.ds.ofdm.rxmer.router import router as rxmer_router
from pypnm_cmts.api.routes.pnm.sg.us.ofdma.pre_equalization.router import (
    router as pre_equalization_router,
)

router = APIRouter()
router.include_router(rxmer_router)
router.include_router(channel_est_coeff_router)
router.include_router(fec_summary_router)
router.include_router(const_display_router)
router.include_router(modulation_profile_router)
router.include_router(pre_equalization_router)

__all__ = [
    "router",
]

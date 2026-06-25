# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(FR-001)
# @spec(FR-006)
# @spec(FR-007)

"""Public facade for the Phase 4.5 runner-aware dispatcher."""

from __future__ import annotations

import logging

from validator.runner_dispatcher_impl import (
    Phase4_5Dispatcher,
    Surface,
    VisualPhaseResult,
    _resolve_registry,
)

logger = logging.getLogger(__name__)

__all__ = [
    "Phase4_5Dispatcher",
    "Surface",
    "VisualPhaseResult",
    "_resolve_registry",
    "logger",
]

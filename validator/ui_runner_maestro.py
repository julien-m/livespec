# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)

"""Public facade for Android Maestro UI runner support."""

from __future__ import annotations

import os
import subprocess
import time
import warnings

from validator.runner_maestro_impl import (
    DEFAULT_COMPARE_THRESHOLD,
    MaestroRunnerHandler,
    UICapabilityResult,
    detect_maestro_runner,
    load_maestro_runner_manifest,
    maestro_runner_manifest_path,
)

__all__ = [
    "DEFAULT_COMPARE_THRESHOLD",
    "MaestroRunnerHandler",
    "UICapabilityResult",
    "detect_maestro_runner",
    "load_maestro_runner_manifest",
    "maestro_runner_manifest_path",
    "os",
    "subprocess",
    "time",
    "warnings",
]

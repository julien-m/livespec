# LiveSpec traceability anchors
# @spec(FR-002)

"""Public facade for Playwright web UI runner support."""

from __future__ import annotations

import os
import subprocess

from validator.runner_web_impl import (
    DEFAULT_COMPARE_THRESHOLD,
    LEGACY_DESIGN_SCREENS_ENV,
    UICapabilityResult,
    WebRunnerHandler,
    detect_web_runner,
    load_web_runner_manifest,
)

__all__ = [
    "DEFAULT_COMPARE_THRESHOLD",
    "LEGACY_DESIGN_SCREENS_ENV",
    "UICapabilityResult",
    "WebRunnerHandler",
    "detect_web_runner",
    "load_web_runner_manifest",
    "os",
    "subprocess",
]

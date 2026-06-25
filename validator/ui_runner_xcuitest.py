# LiveSpec traceability anchors
# @spec(AC-007)
# @spec(AC-013)
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-008)

"""Public facade for iOS/watchOS XCUITest UI runner support."""

from __future__ import annotations

import platform
import subprocess

from validator.runner_xcuitest_impl import (
    DEFAULT_COMPARE_THRESHOLD,
    UICapabilityResult,
    XCUITestRunnerHandler,
    detect_xcuitest_runner,
    load_xcuitest_runner_manifest,
    xcuitest_runner_manifest_path,
)

__all__ = [
    "DEFAULT_COMPARE_THRESHOLD",
    "UICapabilityResult",
    "XCUITestRunnerHandler",
    "detect_xcuitest_runner",
    "load_xcuitest_runner_manifest",
    "platform",
    "subprocess",
    "xcuitest_runner_manifest_path",
]

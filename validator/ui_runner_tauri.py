"""Public facade for Tauri / Rust UI runner support."""

from __future__ import annotations

import shutil

from validator.runner_tauri_impl import (
    DEFAULT_TIMEOUT_SECONDS,
    TAURI_APP_MARKER,
    TAURI_DRIVER_BIN,
    TauriCapability,
    TauriCapabilityStatus,
    TauriRunnerHandler,
    detect_tauri_runner,
)

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "TAURI_APP_MARKER",
    "TAURI_DRIVER_BIN",
    "TauriCapability",
    "TauriCapabilityStatus",
    "TauriRunnerHandler",
    "detect_tauri_runner",
    "shutil",
]

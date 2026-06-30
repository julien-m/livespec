# LiveSpec traceability anchors
# @spec FR-003: Adapter registry — .specs/features/061-conventions-gates-engine/spec.md#fr-003

"""Extension-to-adapter registry for conventions checks."""

from __future__ import annotations

from pathlib import Path

from .base import LanguageAdapter
from .generic import GenericAdapter
from .kotlin_adapter import KotlinAdapter
from .python_adapter import PythonAdapter
from .rust_adapter import RustAdapter
from .swift_adapter import SwiftAdapter
from .typescript_adapter import TypeScriptAdapter

_PYTHON = PythonAdapter()
_TYPESCRIPT = TypeScriptAdapter()
_SWIFT = SwiftAdapter()
_RUST = RustAdapter()
_KOTLIN = KotlinAdapter()
_GENERIC = GenericAdapter()

_ADAPTERS: dict[str, LanguageAdapter] = {
    ".py": _PYTHON,
    ".ts": _TYPESCRIPT,
    ".tsx": _TYPESCRIPT,
    ".js": _TYPESCRIPT,
    ".jsx": _TYPESCRIPT,
    ".swift": _SWIFT,
    ".rs": _RUST,
    ".kt": _KOTLIN,
    ".kts": _KOTLIN,
}


def adapter_for_path(path: Path) -> LanguageAdapter:
    """Return the adapter for `path`, or a partial fallback."""
    return _ADAPTERS.get(path.suffix.lower(), _GENERIC)

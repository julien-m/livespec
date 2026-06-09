# LiveSpec traceability anchors
# @spec(FR-004)

"""Graceful-degradation message when no driver matches the project."""

# Feature 023: driver custom scaffolding & graceful degradation.
# @spec FR-003: Stack name inference from file patterns
# @spec FR-004: Structured degradation message with prefix and sections
# @spec AC-006: Message includes prefix, signals, scaffold cmd, integration link
# @spec AC-008: Stack inference falls back to "unknown" when no signals match

from __future__ import annotations

from pathlib import Path

_INTEGRATION_DOC = ".specs/spec-system.md"

# File signals to detect for diagnostic output (not the same as detect rules).
# Order matters: first match wins for stack inference (AC-008).
_SIGNAL_GLOBS: dict[str, list[str]] = {
    "elixir": ["mix.exs", "*.ex"],
    "ruby": ["Gemfile", "*.rb"],
    "php": ["composer.json", "*.php"],
    "python": ["pyproject.toml", "setup.py", "requirements.txt"],
    "node": ["package.json"],
    "swift": ["Package.swift", "*.xcodeproj"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "jvm": ["build.gradle", "build.gradle.kts", "pom.xml"],
}


def detect_signals(project_root: Path) -> list[str]:
    """Return file-signal hints found at the top of the project.

    Args:
        project_root: Repository root to scan for well-known marker files.

    Returns:
        Sorted unique marker patterns that matched the repository root.
    """
    found: list[str] = []
    for _stack, patterns in _SIGNAL_GLOBS.items():
        for pat in patterns:
            if any(project_root.glob(pat)):
                found.append(pat)
    return sorted(set(found))


def infer_stack_slug(project_root: Path) -> str:
    """Infer a best-effort stack slug for scaffold suggestions.

    Args:
        project_root: Repository root to scan for well-known marker files.

    Returns:
        Stack slug for the first matching marker family, or ``unknown`` when no
        known signals are present (AC-008 fallback).
    """
    for stack, patterns in _SIGNAL_GLOBS.items():
        for pat in patterns:
            if any(project_root.glob(pat)):
                return stack
    return "unknown"


def format_degradation_message(project_root: Path) -> str:
    """Build the structured unsupported-stack message.

    The output starts with the ``⚠ Stack not supported`` prefix and lists
    detected file signals, the suggested custom driver path, the scaffold
    command, and a pointer to the integration documentation (AC-006).

    Args:
        project_root: Repository root whose markers inform the guidance text.

    Returns:
        Human-readable instructions for creating a custom driver manifest.
    """
    signals = detect_signals(project_root)
    stack = infer_stack_slug(project_root)
    custom_path = f".specs/drivers/{stack}.yaml"
    scaffold_cmd = f"livespec spec.driver --new {stack}"
    signals_line = ", ".join(signals) if signals else "(none)"
    return (
        f"⚠ Stack not supported: {stack}\n"
        f"  No driver registered for this stack.\n"
        f"  Detected signals: {signals_line}\n"
        f"  Custom driver path: {custom_path}\n"
        f"  Scaffold with: {scaffold_cmd}\n"
        f"  Integration guide: {_INTEGRATION_DOC}\n"
    )

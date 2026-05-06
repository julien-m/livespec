"""Graceful-degradation message when no driver matches the project."""

# @spec FR-004: Unsupported projects receive a structured degradation message.
# @spec AC-007: The message includes signals, missing capabilities, and scaffold guidance.


from __future__ import annotations

from pathlib import Path

from .schemas import CAPABILITY_NAMES

_INTEGRATION_DOC = ".specs/spec-system.md"

# File signals to detect for diagnostic output (not the same as detect rules).
_SIGNAL_GLOBS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "requirements.txt"],
    "node": ["package.json"],
    "swift": ["Package.swift", "*.xcodeproj"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "jvm": ["build.gradle", "build.gradle.kts", "pom.xml"],
    "elixir": ["mix.exs"],
    "ruby": ["Gemfile"],
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
        Stack slug for the first matching marker family, or ``custom`` when no
        known signals are present.
    """
    for stack, patterns in _SIGNAL_GLOBS.items():
        for pat in patterns:
            if any(project_root.glob(pat)):
                return stack
    return "custom"


def format_degradation_message(project_root: Path) -> str:
    """Build the structured unsupported-stack message.

    Args:
        project_root: Repository root whose markers inform the guidance text.

    Returns:
        Human-readable instructions for creating a custom driver manifest.
    """
    signals = detect_signals(project_root)
    stack = infer_stack_slug(project_root)
    custom_path = f".specs/drivers/{stack}.yaml"
    scaffold_cmd = f"livespec spec-driver --new {stack}"
    signals_line = ", ".join(signals) if signals else "(none)"
    missing = ", ".join(CAPABILITY_NAMES)
    return (
        f"Stack {stack!r} not supported by any built-in driver.\n"
        f"  Detected signals: {signals_line}\n"
        f"  Missing capabilities: {missing}\n"
        f"  Custom driver path: {custom_path}\n"
        f"  Scaffold with: {scaffold_cmd}\n"
        f"  Then connect by following the driver section of {_INTEGRATION_DOC}\n"
    )

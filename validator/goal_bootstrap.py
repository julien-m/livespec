"""Select the immutable project root for goal contract rendering."""

from __future__ import annotations

import os
import shlex
import stat
from dataclasses import dataclass
from pathlib import Path

from .specs_utils import find_specs_root

SPEC_INIT_COMMAND = "spec-init"
_DIRECTORY_FLAGS = frozenset({"--dir", "-D"})


class GoalBootstrapError(Exception):
    """Report an invalid ``spec-init`` bootstrap directory."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"{reason}; correct --dir and rerender the goal")


@dataclass(frozen=True)
class GoalRenderContext:
    """Carry the canonical render root and normalized active flags."""

    project_root: Path
    normalized_flags: tuple[str, ...]


# @spec FR-001: Limit bootstrap to spec-init, FR-002: Parse dir grammar
# @spec FR-003: Bind canonical project root, FR-009: Isolate conventions
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-001
def select_goal_render_context(command: str, flags: str, cwd: Path) -> GoalRenderContext:
    """Select a deterministic goal render root.

    Args:
        command: Canonical LiveSpec command name.
        flags: Raw active flag string.
        cwd: Invocation directory used for relative targets.

    Returns:
        Immutable canonical root and normalized flags.

    Raises:
        GoalBootstrapError: If the spec-init directory grammar or target is invalid.
        SpecsRootNotFoundError: If a non-init command has no initialized ancestor.
    """
    if command != SPEC_INIT_COMMAND:
        project_root = find_specs_root(cwd).parent.resolve(strict=True)
        return GoalRenderContext(project_root, tuple(_normalize_tokens(shlex.split(flags))))

    tokens = _split_flags(flags)
    active_tokens = tokens[: tokens.index("--")] if "--" in tokens else tokens
    directory_values, remaining = _extract_directory_values(active_tokens)
    project_root = _canonical_root(directory_values, cwd)
    normalized = _normalize_tokens(remaining)
    normalized.append(f"--dir={project_root.as_posix()}") if directory_values else None
    return GoalRenderContext(project_root, tuple(sorted(set(normalized))))


def _split_flags(flags: str) -> list[str]:
    try:
        return shlex.split(flags)
    except ValueError as exc:
        raise GoalBootstrapError(f"invalid --flags grammar: {exc}") from exc


def _extract_directory_values(tokens: list[str]) -> tuple[list[str], list[str]]:
    values: list[str] = []
    remaining: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _DIRECTORY_FLAGS:
            if index + 1 >= len(tokens) or tokens[index + 1].startswith("-"):
                raise GoalBootstrapError(f"missing directory value for {token}")
            values.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("--dir=") or token.startswith("-D="):
            value = token.split("=", 1)[1]
            if not value:
                raise GoalBootstrapError(f"missing directory value for {token.split('=', 1)[0]}")
            values.append(value)
            index += 1
            continue
        remaining.append(token)
        index += 1
    return values, remaining


def _canonical_root(values: list[str], cwd: Path) -> Path:
    candidates = values or [cwd.as_posix()]
    roots = [_validate_directory(Path(value), cwd) for value in candidates]
    unique_roots = {root.as_posix() for root in roots}
    if len(unique_roots) != 1:
        raise GoalBootstrapError("conflicting directory values")
    return roots[0]


def _validate_directory(candidate: Path, cwd: Path) -> Path:
    unresolved = candidate if candidate.is_absolute() else cwd / candidate
    try:
        resolved = unresolved.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GoalBootstrapError(f"target cannot be resolved: {unresolved}") from exc
    if not resolved.is_dir():
        raise GoalBootstrapError(f"target is not a directory: {resolved}")
    mode = resolved.stat().st_mode
    if not os.access(resolved, os.R_OK) or not mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
        raise GoalBootstrapError(f"target is not readable: {resolved}")
    return resolved


def _normalize_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("-"):
            index += 1
            continue
        if "=" in token:
            normalized.append(token)
            index += 1
            continue
        if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
            normalized.append(f"{token}={tokens[index + 1]}")
            index += 2
            continue
        normalized.append(token)
        index += 1
    return normalized


__all__ = [
    "SPEC_INIT_COMMAND",
    "GoalBootstrapError",
    "GoalRenderContext",
    "select_goal_render_context",
]

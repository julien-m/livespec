# LiveSpec traceability anchors
# @spec(FR-006)
# @spec(FR-007)

"""User-level Markdown integrations (Level 0 of hook resolution).

This module discovers and parses Markdown integration files in
``~/.config/livespec/*.md``. Each integration may target one or more
LiveSpec commands via its YAML frontmatter.

Eligibility rule (single, non-negotiable):
    A file is treated as an integration iff its frontmatter contains BOTH
    ``integration:`` AND ``commands:`` keys.

    * No frontmatter → silently ignored (free notes tolerated).
    * Frontmatter but missing either key → silently ignored.
    * Both keys present but malformed (invalid YAML, unknown command,
      invalid mode, invalid types) → single stderr warning, file skipped.

This module is the diagnostic-only surface (used by ``/spec-hooks``); the
runtime injection chain lives in :mod:`validator.hook_resolver`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from .command_registry import (
    normalize_command_name,
)
from .command_registry import (
    valid_command_names as registry_valid_command_names,
)

# Source of truth for the canonical command skills directory. Resolved relative
# to this file (validator/integrations.py -> repo root via ../).
LIVESPEC_COMMANDS_DIR = Path(__file__).parent.parent / ".agent-sync" / "skills"

INTEGRATIONS_DIR = Path.home() / ".config" / "livespec"

VALID_PHASES = frozenset({"before", "after"})
VALID_MODES = frozenset({"extend", "override"})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Integration:
    """A parsed user-level integration file (Level 0)."""

    path: Path
    name: str
    commands: tuple[str, ...]
    phase: str
    mode: str
    order: int
    body: str

    def applies_to(self, event: str, command: str) -> bool:
        """Return True if this integration targets the given (event, command)."""
        return self.phase == event and command in self.commands


# ---------------------------------------------------------------------------
# Canonical command registry — single source of truth
# ---------------------------------------------------------------------------


def valid_command_names(commands_dir: Path | None = None) -> frozenset[str]:
    """Return the canonical LiveSpec command registry.

    The registry is derived from ``.agent-sync/skills/spec-*`` directories in
    the repo.
    """
    base = commands_dir or LIVESPEC_COMMANDS_DIR
    return registry_valid_command_names(base)


# ---------------------------------------------------------------------------
# Warning bookkeeping (dedup per-process)
# ---------------------------------------------------------------------------


_warned_keys: set[tuple[str, str]] = set()


def _warn_once(path: Path, message: str) -> None:
    """Emit one stderr warning per (path, message) tuple per process."""
    key = (str(path), message)
    if key in _warned_keys:
        return
    _warned_keys.add(key)
    print(f"⚠ {path}: {message}", file=sys.stderr)


def _reset_warnings_for_tests() -> None:
    """Test helper — clear the warning dedup set."""
    _warned_keys.clear()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Split ``text`` into (frontmatter dict, body string).

    Returns ``(None, text)`` if no frontmatter block is present.
    Raises on broken YAML (caller decides whether the file is *engaged*).
    """
    if not text.startswith("---"):
        return None, text

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, text

    closing_idx: int | None = None
    for idx in range(1, len(lines)):
        stripped = lines[idx].rstrip("\r\n")
        if stripped in ("---", "..."):
            closing_idx = idx
            break

    if closing_idx is None:
        raise ValueError("frontmatter block opened but not closed")

    fm_block = "".join(lines[1:closing_idx])
    body = "".join(lines[closing_idx + 1 :])

    raw: Any = yaml.safe_load(fm_block) if fm_block.strip() else {}
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"frontmatter is not a mapping (got {type(raw).__name__})")
    fm: dict[str, Any] = {}
    raw_dict = cast(dict[Any, Any], raw)
    for k, v in raw_dict.items():
        fm[str(k)] = v
    return fm, body.lstrip("\n")


def _validate_frontmatter(
    fm: dict[str, Any],
    *,
    valid_commands: frozenset[str],
    path: Path,
) -> Integration | None:
    """Validate an *engaged* integration frontmatter. Returns Integration or None.

    Caller must have already verified that ``integration`` and ``commands``
    are both present (the *engagement* test). This function performs the
    deeper shape validation and emits warnings for any malformations.
    """
    raw_name: Any = fm.get("integration")
    if not isinstance(raw_name, str) or not raw_name:
        _warn_once(path, "frontmatter field 'integration:' must be a non-empty string")
        return None
    name: str = raw_name

    raw_commands: Any = fm.get("commands")
    if not isinstance(raw_commands, list) or not raw_commands:
        _warn_once(path, "frontmatter field 'commands:' must be a non-empty list")
        return None
    commands_list: list[str] = []
    for entry in cast(list[Any], raw_commands):
        if not isinstance(entry, str):
            _warn_once(
                path,
                f"frontmatter field 'commands:' must contain strings (got {type(entry).__name__})",
            )
            return None
        commands_list.append(normalize_command_name(entry))

    unknown = [c for c in commands_list if c not in valid_commands]
    if unknown:
        sorted_valid = ", ".join(sorted(valid_commands))
        _warn_once(
            path,
            f'unknown command "{unknown[0]}" — must be one of: {sorted_valid}',
        )
        return None

    raw_phase: Any = fm.get("phase", "before")
    if not isinstance(raw_phase, str) or raw_phase not in VALID_PHASES:
        _warn_once(
            path,
            f'invalid phase "{raw_phase!r}" — must be one of: {sorted(VALID_PHASES)}',
        )
        return None
    phase: str = raw_phase

    raw_mode: Any = fm.get("mode", "extend")
    if not isinstance(raw_mode, str) or raw_mode not in VALID_MODES:
        _warn_once(
            path,
            f'invalid mode "{raw_mode!r}" — must be one of: {sorted(VALID_MODES)}',
        )
        return None
    mode: str = raw_mode

    raw_order: Any = fm.get("order", 100)
    if isinstance(raw_order, bool) or not isinstance(raw_order, int):
        _warn_once(
            path,
            f"frontmatter field 'order:' must be an integer (got {type(raw_order).__name__})",
        )
        return None
    order: int = raw_order

    return Integration(
        path=path,
        name=name,
        commands=tuple(commands_list),
        phase=phase,
        mode=mode,
        order=order,
        body="",  # filled by caller
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def discover_integrations(
    *,
    integrations_dir: Path | None = None,
    commands_dir: Path | None = None,
) -> list[Integration]:
    """Discover and parse all integration files under ``~/.config/livespec/*.md``.

    Returns the list of *engaged* and *well-formed* integrations sorted by
    ``(order, basename)``. Non-engaged files are silently ignored; engaged
    but malformed files trigger a single stderr warning and are skipped.
    """
    base = integrations_dir if integrations_dir is not None else INTEGRATIONS_DIR
    valid_commands = valid_command_names(commands_dir)

    if not base.is_dir():
        return []

    results: list[Integration] = []
    for path in sorted(base.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _warn_once(path, f"cannot read file: {exc}")
            continue

        try:
            fm, body = _parse_frontmatter(text)
        except Exception as exc:
            if text.startswith("---"):
                _warn_once(path, f"broken frontmatter: {exc}")
            continue

        # Engagement test: silently ignored unless BOTH keys are present.
        if fm is None or "integration" not in fm or "commands" not in fm:
            continue

        integration = _validate_frontmatter(
            fm,
            valid_commands=valid_commands,
            path=path,
        )
        if integration is None:
            continue

        results.append(
            Integration(
                path=integration.path,
                name=integration.name,
                commands=integration.commands,
                phase=integration.phase,
                mode=integration.mode,
                order=integration.order,
                body=body,
            )
        )

    # Dedup detection: same (name, sorted commands, phase) triple.
    seen: dict[tuple[str, tuple[str, ...], str], Integration] = {}
    for i in results:
        key = (i.name, tuple(sorted(i.commands)), i.phase)
        if key in seen:
            other = seen[key]
            raise ValueError(
                f'Duplicate integration "{i.name}" for phase={i.phase} '
                f"commands={sorted(i.commands)}: {other.path} vs {i.path}"
            )
        seen[key] = i

    results.sort(key=lambda x: (x.order, x.path.name))
    return results


def resolve_for(
    event: str,
    command: str,
    *,
    integrations_dir: Path | None = None,
    commands_dir: Path | None = None,
) -> list[Integration]:
    """Return integrations targeting ``(event, command)``, in injection order.

    Applies the Level 0 mode rules:
    * if any integration has ``mode: override`` → only that one is kept;
    * multiple ``mode: override`` integrations for the same event → ValueError.
    """
    if event not in VALID_PHASES:
        raise ValueError(f"event must be one of {sorted(VALID_PHASES)}, got: {event!r}")

    all_integrations = discover_integrations(
        integrations_dir=integrations_dir,
        commands_dir=commands_dir,
    )
    command = normalize_command_name(command)
    candidates = [i for i in all_integrations if i.applies_to(event, command)]

    overrides = [i for i in candidates if i.mode == "override"]
    if len(overrides) > 1:
        paths = ", ".join(str(o.path) for o in overrides)
        raise ValueError(f"Multiple override integrations for event {event}-{command}: {paths}")
    if overrides:
        return [overrides[0]]
    return candidates


__all__ = [
    "INTEGRATIONS_DIR",
    "LIVESPEC_COMMANDS_DIR",
    "VALID_MODES",
    "VALID_PHASES",
    "Integration",
    "_reset_warnings_for_tests",
    "discover_integrations",
    "resolve_for",
    "valid_command_names",
]

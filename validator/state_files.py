"""State-file frontmatter validator.

Spec anchors (Chantier 4 / Feature 013 — see
``.specs/features/013-state-model-identity-resolution/spec.md``):

- @spec FR-005: Shared frontmatter schema.
- @spec FR-006: ``livespec validate --state-files`` subcommand.

Validates that every known state file under ``.specs/`` carries the canonical
YAML frontmatter defined in ``system/state-files-schema.md``:

- ``schema_version: int`` (currently ``1``)
- ``owner_command: str`` (e.g. ``spec.feature``, ``spec.implement``)
- ``feature_slug: str`` (matches :data:`validator.identity.SLUG_REGEX` —
  except for project-global state files where the field is the literal ``"-"``)
- ``created_at: str`` (ISO date ``YYYY-MM-DD``)
- ``updated_at: str`` (ISO date ``YYYY-MM-DD``)
- ``current_state: str`` (one of ``Pending | InProgress | Done | Blocked``)

Returns a list of :class:`StateFileViolation` per file. The CLI wrapper exits
non-zero when any violation is found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]

from .identity import PLACEHOLDER_LITERAL, SLUG_REGEX

# @spec FR-005: Allowed states — spec.md#fr-005
ALLOWED_STATES = {"Pending", "InProgress", "Done", "Blocked"}

# @spec FR-005: State-file basenames recognised by the validator — spec.md#fr-005
KNOWN_STATE_FILENAMES = {
    "pipeline.md",
    "progress.md",
    "ship.md",
    "preflight.md",
}

REQUIRED_KEYS = (
    "schema_version",
    "owner_command",
    "feature_slug",
    "created_at",
    "updated_at",
    "current_state",
)

ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class StateFileViolation:
    """A single schema violation found in a state file."""

    path: Path
    rule: str
    message: str

    def __str__(self) -> str:  # pragma: no cover — formatting helper
        return f"{self.path}: [{self.rule}] {self.message}"


@dataclass
class StateFilesReport:
    """Aggregated report from a state-files validation run."""

    files_checked: int = 0
    violations: list[StateFileViolation] = field(
        default_factory=lambda: []  # type: ignore[var-annotated]
    )

    @property
    def ok(self) -> bool:
        return not self.violations


def _is_project_global_state_file(path: Path) -> bool:
    """``.specs/ship.md`` and ``.specs/preflight.md`` are project-global, not feature-scoped."""
    return path.parent.name == ".specs"


def _validate_keys(meta: dict[str, Any], path: Path) -> list[StateFileViolation]:
    violations: list[StateFileViolation] = []
    for key in REQUIRED_KEYS:
        if key not in meta:
            violations.append(
                StateFileViolation(path, "missing_key", f"required frontmatter key {key!r} absent")
            )
    return violations


def _validate_value_shapes(meta: dict[str, Any], path: Path) -> list[StateFileViolation]:
    violations: list[StateFileViolation] = []

    # schema_version
    if "schema_version" in meta and not isinstance(meta["schema_version"], int):
        violations.append(
            StateFileViolation(
                path,
                "wrong_type",
                f"schema_version must be int (got {type(meta['schema_version']).__name__})",
            )
        )

    # owner_command
    if "owner_command" in meta and not (
        isinstance(meta["owner_command"], str) and meta["owner_command"].strip()
    ):
        violations.append(
            StateFileViolation(path, "wrong_type", "owner_command must be non-empty string")
        )

    # feature_slug — project-global files use "-" sentinel
    slug = meta.get("feature_slug")
    if isinstance(slug, str):
        if slug == PLACEHOLDER_LITERAL:
            violations.append(
                StateFileViolation(
                    path, "placeholder_leak", f"feature_slug must not be {PLACEHOLDER_LITERAL!r}"
                )
            )
        elif _is_project_global_state_file(path):
            if slug != "-":
                violations.append(
                    StateFileViolation(
                        path,
                        "wrong_value",
                        f'feature_slug for project-global file must be "-" (got {slug!r})',
                    )
                )
        elif not SLUG_REGEX.match(slug):
            violations.append(
                StateFileViolation(
                    path,
                    "wrong_value",
                    f"feature_slug fails canonical regex {SLUG_REGEX.pattern!r} (got {slug!r})",
                )
            )
    elif "feature_slug" in meta:
        violations.append(
            StateFileViolation(path, "wrong_type", "feature_slug must be str")
        )

    # created_at / updated_at
    for date_key in ("created_at", "updated_at"):
        if date_key in meta:
            value = meta[date_key]
            value_str = str(value)
            if not ISO_DATE_REGEX.match(value_str):
                violations.append(
                    StateFileViolation(
                        path,
                        "wrong_format",
                        f"{date_key} must be ISO date YYYY-MM-DD (got {value!r})",
                    )
                )

    # current_state
    if "current_state" in meta:
        state = meta["current_state"]
        if state not in ALLOWED_STATES:
            violations.append(
                StateFileViolation(
                    path,
                    "wrong_value",
                    f"current_state must be one of {sorted(ALLOWED_STATES)} (got {state!r})",
                )
            )

    return violations


def _validate_blocked_has_reason(meta: dict[str, Any], path: Path) -> list[StateFileViolation]:
    """When current_state is Blocked, a non-empty 'reason' field is mandatory."""
    if meta.get("current_state") != "Blocked":
        return []
    reason = meta.get("reason")
    if not (isinstance(reason, str) and reason.strip()):
        return [
            StateFileViolation(
                path,
                "missing_reason",
                "current_state=Blocked requires a non-empty 'reason' field",
            )
        ]
    return []


def discover_state_files(specs_root: Path) -> list[Path]:
    """Find every state file under ``specs_root``.

    Recursively scans for files whose basename is in
    :data:`KNOWN_STATE_FILENAMES`. Returns absolute paths.
    """
    if not specs_root.is_dir():
        return []
    found: list[Path] = []
    for path in specs_root.rglob("*"):
        if path.is_file() and path.name in KNOWN_STATE_FILENAMES:
            found.append(path)
    return sorted(found)


def validate_state_file(path: Path) -> list[StateFileViolation]:
    """Validate a single state file's frontmatter.

    Returns an empty list on success, otherwise one or more
    :class:`StateFileViolation` entries.
    """
    try:
        post = frontmatter.load(str(path))
    except Exception as exc:
        return [
            StateFileViolation(path, "parse_error", f"could not parse frontmatter ({exc!s})")
        ]
    raw_meta: Any = post.metadata if post.metadata else {}  # type: ignore[no-any-expr]
    meta: dict[str, Any] = (
        {str(k): v for k, v in raw_meta.items()}  # type: ignore[reportUnknownVariableType]
        if isinstance(raw_meta, dict)
        else {}
    )

    violations: list[StateFileViolation] = []
    violations.extend(_validate_keys(meta, path))
    violations.extend(_validate_value_shapes(meta, path))
    violations.extend(_validate_blocked_has_reason(meta, path))
    return violations


def validate_state_files(specs_root: Path) -> StateFilesReport:
    """Validate every state file under ``specs_root``.

    Returns a :class:`StateFilesReport` aggregating per-file violations.
    """
    report = StateFilesReport()
    for path in discover_state_files(specs_root):
        report.files_checked += 1
        report.violations.extend(validate_state_file(path))
    return report

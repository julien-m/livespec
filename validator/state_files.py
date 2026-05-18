"""State-file frontmatter validator.

Spec anchors (Chantier 4 / Feature 013 — see
``.specs/features/013-state-model-identity-resolution/spec.md``):

- @spec FR-005: Shared frontmatter schema.
- @spec FR-006: ``livespec validate --state-files`` subcommand.
- @spec FR-006 (migrate sub-flag): ``--migrate`` adds missing frontmatter to
  legacy state files in place. Mentioned as future work in
  ``system/state-files-schema.md § Migration of legacy state files``.

Validates that every known state file under ``.specs/`` carries the canonical
YAML frontmatter defined in ``system/state-files-schema.md``:

- ``schema_version: int`` (currently ``1``)
- ``owner_command: str`` (e.g. ``spec-feature``, ``spec-implement``)
- ``feature_slug: str`` (matches :data:`validator.identity.SLUG_REGEX` —
  except for project-global state files where the field is the literal ``"-"``)
- ``created_at: str`` (ISO date ``YYYY-MM-DD``)
- ``updated_at: str`` (ISO date ``YYYY-MM-DD``)
- ``current_state: str`` (one of ``Pending | InProgress | Done | Blocked``)

Returns a list of :class:`StateFileViolation` per file. The CLI wrapper exits
non-zero when any violation is found.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]

from .identity import PLACEHOLDER_LITERAL, SLUG_REGEX
from .locks import write_with_hash_check

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
    elif "owner_command" in meta:
        expected_owner = _infer_owner_command(path)
        if expected_owner != "unknown" and meta["owner_command"] != expected_owner:
            violations.append(
                StateFileViolation(
                    path,
                    "wrong_value",
                    f"owner_command must be {expected_owner!r} (got {meta['owner_command']!r})",
                )
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


# ─── Migration (FR-006 sub-flag --migrate) ───────────────────────────────────

# Filename → owner_command mapping.
_OWNER_COMMAND_BY_FILENAME = {
    "pipeline.md": "spec-feature",
    "progress.md": "spec-implement",
    "ship.md": "spec-ship",
    "preflight.md": "spec-preflight",
}

# Body markers used to infer the legacy state when no `current_state` field is set.
_BLOCKED_MARKERS = ("Blocked", "BLOCKED", "blocked by")
_DONE_MARKERS = ("| Done |", " Done ", "All steps Done")
_IN_PROGRESS_MARKERS = ("In Progress", "in_progress")


@dataclass
class MigrationOutcome:
    """Per-file outcome of a ``--migrate`` run."""

    path: Path
    action: str  # "added", "completed", "already_compliant", "skipped"
    added_keys: list[str] = field(default_factory=lambda: [])  # type: ignore[var-annotated]
    note: str | None = None

    def __str__(self) -> str:  # pragma: no cover — formatting helper
        keys = f" [{', '.join(self.added_keys)}]" if self.added_keys else ""
        suffix = f" ({self.note})" if self.note else ""
        return f"{self.path}: {self.action}{keys}{suffix}"


@dataclass
class MigrationReport:
    """Aggregated outcome of a ``--migrate`` run."""

    files_checked: int = 0
    outcomes: list[MigrationOutcome] = field(
        default_factory=lambda: []  # type: ignore[var-annotated]
    )

    @property
    def added_count(self) -> int:
        return sum(1 for o in self.outcomes if o.action == "added")

    @property
    def completed_count(self) -> int:
        return sum(1 for o in self.outcomes if o.action == "completed")

    @property
    def already_compliant_count(self) -> int:
        return sum(1 for o in self.outcomes if o.action == "already_compliant")


def _infer_owner_command(path: Path) -> str:
    return _OWNER_COMMAND_BY_FILENAME.get(path.name, "unknown")


def _infer_feature_slug(path: Path, specs_root: Path) -> str:
    """Return the feature slug for ``path`` or the ``"-"`` sentinel for project-global files."""
    if _is_project_global_state_file(path):
        return "-"
    try:
        rel = path.resolve().relative_to((specs_root / "features").resolve())
    except ValueError:
        return "-"
    parts = rel.parts
    if not parts:
        return "-"
    candidate = parts[0]
    return candidate if SLUG_REGEX.match(candidate) else "-"


def _git_dates(path: Path) -> tuple[str | None, str | None]:
    """Return ``(created_at, updated_at)`` from git history, or ``(None, None)``."""
    try:
        first = subprocess.run(
            ["git", "log", "--format=%ad", "--date=short", "--diff-filter=A", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd=path.parent,
        )
        last = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd=path.parent,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    created = (
        first.stdout.strip().splitlines()[-1]
        if first.returncode == 0 and first.stdout
        else None
    )
    updated = last.stdout.strip() if last.returncode == 0 and last.stdout else None
    if created and not ISO_DATE_REGEX.match(created):
        created = None
    if updated and not ISO_DATE_REGEX.match(updated):
        updated = None
    return created, updated


def _filesystem_date(path: Path) -> str:
    """Return ``YYYY-MM-DD`` for the file's mtime (fallback when git has no record)."""
    ts = path.stat().st_mtime
    return _dt.date.fromtimestamp(ts).isoformat()


def _infer_current_state(meta: dict[str, Any], body: str) -> str:
    """Heuristic state inference for a legacy file body.

    Order: meta override > Blocked markers > InProgress markers > Done markers > Done default.
    Done is the safe default because legacy files predate the validator and the project
    has been shipping features for weeks — most of these are historical, completed records.
    """
    existing = meta.get("current_state")
    if isinstance(existing, str) and existing in ALLOWED_STATES:
        return existing
    # Only treat as Blocked if a blocked-marker is present AND the file does not
    # also show a Done outcome (avoids flagging completed-with-recovery files).
    if (
        any(marker in body for marker in _BLOCKED_MARKERS)
        and "Blocked" in body
        and "Done" not in body
    ):
        return "Blocked"
    if any(marker in body for marker in _IN_PROGRESS_MARKERS) and "Done" not in body:
        return "InProgress"
    if any(marker in body for marker in _DONE_MARKERS):
        return "Done"
    # Conservative default for historical files.
    return "Done"


def migrate_state_file(path: Path, specs_root: Path) -> MigrationOutcome:
    """Add missing canonical frontmatter to a single state file in place.

    The file is rewritten only if at least one required key was missing or
    invalid. Existing keys are preserved as-is (no overwrite of user-set values).
    Body content (after the frontmatter) is preserved verbatim.

    Args:
        path: Absolute path to the state file.
        specs_root: Root of ``.specs/`` (used to derive ``feature_slug``).

    Returns:
        :class:`MigrationOutcome` describing what was done.
    """
    try:
        post = frontmatter.load(str(path))
    except Exception as exc:
        return MigrationOutcome(path, "skipped", note=f"parse error: {exc!s}")

    raw_meta: Any = post.metadata if post.metadata else {}  # type: ignore[no-any-expr]
    meta: dict[str, Any] = (
        {str(k): v for k, v in raw_meta.items()}  # type: ignore[reportUnknownVariableType]
        if isinstance(raw_meta, dict)
        else {}
    )
    body: str = post.content  # type: ignore[no-any-expr]

    # Compute defaults
    git_created, git_updated = _git_dates(path)
    fs_date = _filesystem_date(path)
    defaults: dict[str, Any] = {
        "schema_version": 1,
        "owner_command": _infer_owner_command(path),
        "feature_slug": _infer_feature_slug(path, specs_root),
        "created_at": git_created or fs_date,
        "updated_at": git_updated or fs_date,
        "current_state": _infer_current_state(meta, body),
    }

    # Merge strategy: add missing keys; replace keys whose existing value fails
    # the schema. Hand-set keys that already validate are preserved verbatim.
    added: list[str] = []
    fixed: list[str] = []
    new_meta = dict(meta)

    for key, value in defaults.items():
        if key not in new_meta or new_meta[key] in (None, ""):
            new_meta[key] = value
            added.append(key)
            continue
        # Existing key: re-validate just this key by simulating a single-key meta
        single_key_check = _validate_value_shapes({key: new_meta[key]}, path)
        if single_key_check:
            new_meta[key] = value
            fixed.append(key)

    # If current_state is Blocked, ensure a 'reason' is present (or stub it)
    if new_meta.get("current_state") == "Blocked" and not (
        isinstance(new_meta.get("reason"), str) and str(new_meta.get("reason", "")).strip()
    ):
        new_meta["reason"] = "(legacy migration: reason not recorded)"
        added.append("reason")

    changed = added + fixed
    if not changed:
        return MigrationOutcome(path, "already_compliant")

    # Re-serialise and write atomically with hash check.
    new_post = frontmatter.Post(body, **new_meta)  # type: ignore[no-untyped-call]
    serialised = frontmatter.dumps(new_post) + "\n"  # type: ignore[no-untyped-call]
    write_with_hash_check(path, serialised)

    action = "completed" if meta else "added"
    note = f"fixed: {', '.join(fixed)}" if fixed else None
    return MigrationOutcome(path, action, added_keys=added + fixed, note=note)


def migrate_state_files(specs_root: Path) -> MigrationReport:
    """Migrate every state file under ``specs_root``.

    Files already in compliance are skipped (no rewrite).
    """
    report = MigrationReport()
    for path in discover_state_files(specs_root):
        report.files_checked += 1
        report.outcomes.append(migrate_state_file(path, specs_root))
    return report

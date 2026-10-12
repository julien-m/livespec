# @spec FR-005, FR-006: Versioned repo baseline file
#   .specs/features/082-conventions-gate-signal/spec.md#fr-006

"""Versioned repo-scope conventions baseline: model, load, render and explicit write."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from .conventions_gate_types import GateResult, GateSeverity, GateViolation

BASELINE_RELATIVE_PATH = Path(".specs/conventions/baseline.json")
BASELINE_SCHEMA_VERSION = 1
BASELINE_SCOPE = "repo"
BASELINE_INVALID = "baseline_invalid"
WRITE_BASELINE_HINT = (
    "Run `livespec conventions verify --feature repo --write-baseline` to rewrite the baseline."
)
# System findings that already produce blockers are never recorded as debt.
_SYSTEM_RULES = frozenset({"linter_timeout", "file_encoding_error", "file_read_error"})
# `_unparsed_linter_failure` reports a crashed linter at the repository root path.
_TOOL_FAILURE_PATH = "."

PreviousBaseline = Literal["absent", "valid", "invalid"]
BaselineKey = tuple[str, str]


class BaselineError(ValueError):
    """Raised when the baseline file cannot be read or violates its schema."""


@dataclass(frozen=True)
class BaselineEntry:
    """Recorded error debt for one rule id and path (one message per occurrence)."""

    rule_id: str
    path: str
    count: int
    messages: tuple[str, ...]
    rule_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form stored in the baseline file."""
        return {
            "rule_id": self.rule_id,
            "path": self.path,
            "count": self.count,
            "messages": list(self.messages),
            "rule_ids": list(self.rule_ids),
        }


@dataclass(frozen=True)
class ConventionsBaseline:
    """Loaded baseline with the identity of the exact file bytes."""

    entries: tuple[BaselineEntry, ...]
    sha256: str

    def by_key(self) -> dict[BaselineKey, BaselineEntry]:
        """Index entries by `(rule_id, path)`."""
        return {(entry.rule_id, entry.path): entry for entry in self.entries}


@dataclass(frozen=True)
class BaselineWriteSummary:
    """Outcome of an explicit baseline write."""

    path: str
    recorded: int
    added: int
    removed: int
    previous: PreviousBaseline

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form reported by the CLI."""
        return {
            "path": self.path,
            "recorded": self.recorded,
            "added": self.added,
            "removed": self.removed,
            "previous": self.previous,
        }


def baseline_path(project_root: Path) -> Path:
    """Return the versioned baseline path of a project."""
    return project_root / BASELINE_RELATIVE_PATH


def baseline_sha256(project_root: Path) -> str:
    """Return the sha256 of the current baseline bytes, or an empty string when absent."""
    path = baseline_path(project_root)
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def severity_value(violation: GateViolation) -> str:
    """Return the plain severity string of a violation."""
    severity = violation.severity
    return severity.value if isinstance(severity, GateSeverity) else severity


def is_baselinable(violation: GateViolation) -> bool:
    """Return True for error findings that may be recorded as debt.

    Warnings, blocking system findings and linter tool failures are never recorded:
    baselining a crashed linter would hide every finding of that linter.
    """
    if severity_value(violation) != "error" or violation.rule_id in _SYSTEM_RULES:
        return False
    return not (violation.source == "linter" and violation.path == _TOOL_FAILURE_PATH)


def load_baseline(project_root: Path) -> ConventionsBaseline | None:
    """Load the baseline, returning None when the file does not exist.

    Raises:
        BaselineError: The file is unreadable, not JSON or violates the schema.
    """
    path = baseline_path(project_root)
    if not path.exists():
        return None
    try:
        data = path.read_bytes()
        raw: object = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} unreadable: {exc}") from exc
    return ConventionsBaseline(_parse_baseline(raw), hashlib.sha256(data).hexdigest())


def build_baseline_entries(violations: Iterable[GateViolation]) -> tuple[BaselineEntry, ...]:
    """Group baselinable error violations into sorted baseline entries."""
    grouped: dict[BaselineKey, list[GateViolation]] = {}
    for violation in violations:
        if is_baselinable(violation):
            grouped.setdefault((violation.rule_id, violation.path), []).append(violation)
    return tuple(
        BaselineEntry(
            rule_id=rule_id,
            path=path,
            count=len(items),
            messages=tuple(sorted(item.message for item in items)),
            rule_ids=tuple(sorted({rule for item in items for rule in item.rule_ids})),
        )
        for (rule_id, path), items in sorted(grouped.items())
    )


def render_baseline(entries: tuple[BaselineEntry, ...]) -> str:
    """Serialize entries deterministically (sorted keys, no timestamp)."""
    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "scope": BASELINE_SCOPE,
        "summary": {"entries": len(entries), "violations": sum(e.count for e in entries)},
        "entries": [entry.to_dict() for entry in entries],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_baseline(project_root: Path, result: GateResult) -> BaselineWriteSummary:
    """Record the current repo-scope error violations as the new baseline."""
    previous, old_counts = _previous_counts(project_root)
    entries = build_baseline_entries(result.violations)
    new_counts = Counter({(entry.rule_id, entry.path): entry.count for entry in entries})
    path = baseline_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_baseline(entries), encoding="utf-8")
    return BaselineWriteSummary(
        path=BASELINE_RELATIVE_PATH.as_posix(),
        recorded=sum(new_counts.values()),
        added=sum((new_counts - old_counts).values()),
        removed=sum((old_counts - new_counts).values()),
        previous=previous,
    )


def _previous_counts(project_root: Path) -> tuple[PreviousBaseline, Counter[BaselineKey]]:
    try:
        old = load_baseline(project_root)
    except BaselineError:
        return "invalid", Counter()
    if old is None:
        return "absent", Counter()
    return "valid", Counter({(e.rule_id, e.path): e.count for e in old.entries})


def _parse_baseline(raw: object) -> tuple[BaselineEntry, ...]:
    if not isinstance(raw, dict):
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} root must be an object")
    payload = cast(dict[str, object], raw)
    if payload.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} schema_version must be 1")
    if payload.get("scope") != BASELINE_SCOPE:
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} scope must be repo")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entries must be a list")
    return tuple(_parse_entry(item) for item in cast(list[object], entries))


def _parse_entry(item: object) -> BaselineEntry:
    if not isinstance(item, dict):
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entry must be an object")
    entry = cast(dict[str, object], item)
    rule_id, path, count = entry.get("rule_id"), entry.get("path"), entry.get("count")
    if not isinstance(rule_id, str) or not isinstance(path, str):
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entry needs string rule_id and path")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entry {rule_id} {path} count invalid")
    messages = _strings(entry.get("messages"), "messages")
    if len(messages) != count:
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entry {rule_id} {path} messages != count")
    return BaselineEntry(
        rule_id, path, count, messages, _strings(entry.get("rule_ids", []), "rule_ids")
    )


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entry {field} must be a string list")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise BaselineError(f"{BASELINE_RELATIVE_PATH} entry {field} must be a string list")
    return tuple(cast(list[str], items))

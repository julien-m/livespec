"""Typed records shared by the runtime install, selection, inspection and defect flows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias, cast

from .errors import RuntimeSnapshotError
from .shim_core import COMMIT_RE, RUNTIME_ID_RE

JsonValue: TypeAlias = str | int | bool | list["JsonValue"] | dict[str, "JsonValue"] | None
JsonObject: TypeAlias = dict[str, JsonValue]

MANIFEST_NAME = ".livespec-runtime.json"
SCHEMA_VERSION = 1
DIGEST_PREFIX = "sha256:"
# Content digest "sha256:" followed by exactly 64 lowercase hex characters.
_DIGEST_RE = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
# Top-level directories of the LiveSpec repository that never ship in a snapshot (FR-001).
EXCLUDED_TOP_LEVEL = frozenset({".specs", "tests"})
# Runtime data under the excluded ``tests/`` tree: the AST detector fixtures and the
# deterministic test files the bundled conventions catalogs cite as evidence. A
# trailing slash covers a whole directory; other entries are exact files.
SNAPSHOT_TEST_EVIDENCE = (
    "tests/fixtures/conventions_ast/",
    "tests/test_conventions_ars_rules.py",
    "tests/test_conventions_ast_multilang.py",
    "tests/test_conventions_source_family_checks.py",
)


def ships_in_snapshot(path: str) -> bool:
    """Return whether a committed tree path belongs to a runtime snapshot (FR-001)."""
    if path.split("/", 1)[0] not in EXCLUDED_TOP_LEVEL:
        return True
    return any(
        path.startswith(entry) if entry.endswith("/") else path == entry
        for entry in SNAPSHOT_TEST_EVIDENCE
    )


LOCK_RELPATH = Path(".specs") / "livespec.lock"
LIVESPEC_PATH_RELPATH = Path(".specs") / ".livespec-path"
PROJECT_VERSION_RELPATH = Path(".specs") / "livespec-version"
MANIFEST_KEYS = frozenset(
    {"schema", "runtime_id", "livespec_version", "commit", "source", "created_at", "content_digest"}
)


class FindingSeverity(StrEnum):
    """Severities shared with ``livespec doctor`` findings."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# @spec FR-002: Manifest model — .specs/features/083-pinned-runtime-isolation/spec.md#fr-002
@dataclass(frozen=True)
class RuntimeManifest:
    """Identity and integrity record stored as ``.livespec-runtime.json`` in a snapshot."""

    runtime_id: str
    livespec_version: int
    commit: str
    source: str
    created_at: str
    content_digest: str
    schema: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        """Return the manifest as a JSON-ready mapping."""
        return {
            "schema": self.schema,
            "runtime_id": self.runtime_id,
            "livespec_version": self.livespec_version,
            "commit": self.commit,
            "source": self.source,
            "created_at": self.created_at,
            "content_digest": self.content_digest,
        }


def _is_utc_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.utcoffset() == timedelta(0)


def _manifest_errors(data: dict[str, object]) -> list[str]:
    """Return schema-1 violations of a decoded manifest (empty when valid)."""
    text_keys = ("runtime_id", "commit", "source", "created_at", "content_digest")
    if not all(isinstance(data[key], str) for key in text_keys):
        return ["field types"]
    runtime_id, commit = str(data["runtime_id"]), str(data["commit"])
    version, schema = data["livespec_version"], data["schema"]
    checks = {
        "schema": type(schema) is int and schema == SCHEMA_VERSION,
        "runtime_id": bool(RUNTIME_ID_RE.match(runtime_id)),
        "commit": bool(COMMIT_RE.match(commit)),
        "version/prefix": type(version) is int and runtime_id == f"{version}-{commit[:12]}",
        "content_digest": bool(_DIGEST_RE.match(str(data["content_digest"]))),
        "created_at": _is_utc_timestamp(str(data["created_at"])),
        "source": Path(str(data["source"])).is_absolute(),
    }
    return [name for name, valid in checks.items() if not valid]


# @spec FR-002: Strict manifest schema
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-002
def manifest_from_dict(raw: object, path: Path) -> RuntimeManifest:
    """Validate a decoded manifest mapping strictly against schema 1.

    Args:
        raw: Decoded JSON value.
        path: Manifest path used in error messages.

    Returns:
        The validated manifest.

    Raises:
        RuntimeSnapshotError: If keys, types, formats or the id/version/commit relation
            do not match schema 1 (integer schema 1, ``<VERSION>-<sha12>`` id, full hex
            commit, ``sha256:`` + 64 hex digest, UTC ISO-8601 ``created_at``).
    """
    if not isinstance(raw, dict):
        raise RuntimeSnapshotError(f"runtime manifest is not a JSON object: {path}")
    # json.loads yields untyped dicts; keys are JSON strings, values are checked below.
    data = cast("dict[str, object]", raw)
    if frozenset(data) != MANIFEST_KEYS:
        raise RuntimeSnapshotError(f"invalid runtime manifest keys: {path}")
    errors = _manifest_errors(data)
    if errors:
        raise RuntimeSnapshotError(f"invalid runtime manifest ({', '.join(errors)}): {path}")
    return RuntimeManifest(
        runtime_id=str(data["runtime_id"]),
        livespec_version=cast("int", data["livespec_version"]),
        commit=str(data["commit"]),
        source=str(data["source"]),
        created_at=str(data["created_at"]),
        content_digest=str(data["content_digest"]),
    )


@dataclass(frozen=True)
class InstallResult:
    """Outcome of ``livespec runtime install``."""

    runtime_id: str
    snapshot: Path
    status: str
    activated: bool
    shim: Path
    current: Path

    def to_dict(self) -> JsonObject:
        """Return the JSON payload printed by ``install --json``."""
        return {
            "runtime_id": self.runtime_id,
            "snapshot": str(self.snapshot),
            "status": self.status,
            "activated": self.activated,
            "shim": str(self.shim),
            "current": str(self.current),
        }


@dataclass(frozen=True)
class LinkReport:
    """LiveSpec-owned link outcomes of a pin, upgrade or dev selection."""

    retargeted: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()

    def to_dict(self) -> JsonObject:
        """Return link outcomes as sorted string lists."""
        return {
            "retargeted": list(self.retargeted),
            "missing": list(self.missing),
            "unchanged": list(self.unchanged),
        }


@dataclass(frozen=True)
class SelectionResult:
    """Outcome of ``pin``, ``upgrade`` or ``dev`` on one project."""

    project: Path
    mode: str
    lock: JsonObject
    previous_lock: JsonValue
    runtime_root: Path
    changed: bool
    links: LinkReport = field(default_factory=LinkReport)
    warnings: tuple[str, ...] = ()
    old_runtime_id: str | None = None
    migration_required: bool = False

    def to_dict(self) -> JsonObject:
        """Return the JSON payload printed by the selection commands."""
        payload: JsonObject = {
            "project": str(self.project),
            "mode": self.mode,
            "lock": self.lock,
            "previous_lock": self.previous_lock,
            "runtime_root": str(self.runtime_root),
            "livespec_path": str(self.runtime_root),
            "changed": self.changed,
            "links": self.links.to_dict(),
            "warnings": list(self.warnings),
        }
        if self.old_runtime_id is not None:
            payload["old_runtime_id"] = self.old_runtime_id
            payload["new_runtime_id"] = self.lock.get("runtime_id")
            payload["migration_required"] = self.migration_required
            payload["recovery"] = "/spec-migrate" if self.migration_required else None
        return payload


@dataclass(frozen=True)
class RuntimeFinding:
    """One runtime drift diagnostic shared by ``runtime status`` and ``doctor``."""

    code: str
    severity: FindingSeverity
    message: str
    path: str | None = None
    suggested_action: str | None = None

    def to_dict(self) -> JsonObject:
        """Return the finding as a JSON-ready mapping."""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
            "suggested_action": self.suggested_action,
        }


def require_snapshot_identity(manifest: RuntimeManifest, runtime_id: str, path: Path) -> None:
    """Raise when a manifest does not describe the expected runtime id.

    Args:
        manifest: Manifest read from the snapshot.
        runtime_id: Expected runtime id (directory name).
        path: Snapshot path used in the error message.

    Raises:
        RuntimeSnapshotError: If the manifest runtime id or commit prefix differs.
    """
    expected = f"{manifest.livespec_version}-{manifest.commit[:12]}"
    if manifest.runtime_id != runtime_id or expected != runtime_id:
        raise RuntimeSnapshotError(f"runtime manifest identity mismatch for {runtime_id}: {path}")

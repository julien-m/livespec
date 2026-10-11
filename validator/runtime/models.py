"""Typed records shared by the runtime install, selection, inspection and defect flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias, cast

from .errors import RuntimeSnapshotError

JsonValue: TypeAlias = str | int | bool | list["JsonValue"] | dict[str, "JsonValue"] | None
JsonObject: TypeAlias = dict[str, JsonValue]

MANIFEST_NAME = ".livespec-runtime.json"
SCHEMA_VERSION = 1
DIGEST_PREFIX = "sha256:"
# Top-level directories of the LiveSpec repository that never ship in a snapshot (FR-001).
EXCLUDED_TOP_LEVEL = frozenset({".specs", "tests"})
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


def manifest_from_dict(raw: object, path: Path) -> RuntimeManifest:
    """Validate a decoded manifest mapping.

    Args:
        raw: Decoded JSON value.
        path: Manifest path used in error messages.

    Returns:
        The validated manifest.

    Raises:
        RuntimeSnapshotError: If keys, types or schema do not match schema 1.
    """
    if not isinstance(raw, dict):
        raise RuntimeSnapshotError(f"runtime manifest is not a JSON object: {path}")
    # json.loads yields untyped dicts; keys are JSON strings, values are checked below.
    data = cast("dict[str, object]", raw)
    if frozenset(data) != MANIFEST_KEYS:
        raise RuntimeSnapshotError(f"invalid runtime manifest keys: {path}")
    text_keys = ("runtime_id", "commit", "source", "created_at", "content_digest")
    if not all(isinstance(data[key], str) for key in text_keys):
        raise RuntimeSnapshotError(f"invalid runtime manifest field types: {path}")
    version = data["livespec_version"]
    schema = data["schema"]
    if type(version) is not int or schema != SCHEMA_VERSION:
        raise RuntimeSnapshotError(f"invalid runtime manifest schema or version: {path}")
    return RuntimeManifest(
        runtime_id=str(data["runtime_id"]),
        livespec_version=version,
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

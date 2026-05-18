"""Run-artifact data model and recorder.

# @spec FR-005: RunArtifact JSON schema
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-005
# @spec FR-006: artifact emitter wiring
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-006
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .command_registry import short_command_name
from .exceptions import ArtifactMalformed

MAX_STREAM_BYTES = 1_048_576  # 1 MB per stream (mitigation b)
ROTATION_KEEP = 20


def _empty_str_list() -> list[str]:
    """Typed default factory for ``list[str]`` dataclass fields."""
    return []


@dataclass
class GitState:
    """Snapshot of git state at a point in time."""

    branch: str = ""
    head_sha: str = ""
    dirty: list[str] = field(default_factory=_empty_str_list)


@dataclass
class FsChange:
    """A single filesystem change observed during a run."""

    path: str
    change: str  # "create" | "modify" | "delete"


@dataclass
class RunArtifact:
    """Canonical artifact captured for a single `/spec.*` invocation."""

    command: str
    timestamp: str  # ISO 8601 UTC
    flags: list[str]
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    cwd: str
    git_state_before: GitState
    git_state_after: GitState
    fs_observed: list[FsChange]

    def to_dict(self) -> dict[str, Any]:
        """Render as a JSON-serializable dict."""
        return {
            "command": self.command,
            "timestamp": self.timestamp,
            "flags": list(self.flags),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "cwd": self.cwd,
            "git_state_before": asdict(self.git_state_before),
            "git_state_after": asdict(self.git_state_after),
            "fs_observed": [asdict(c) for c in self.fs_observed],
        }

    def write(self, runs_dir: Path) -> Path:
        """Atomically write the artifact to ``runs_dir``.

        Returns:
            The final artifact path.
        """
        runs_dir.mkdir(parents=True, exist_ok=True)
        # Filename-safe timestamp: replace ':' with '-'.
        ts = self.timestamp.replace(":", "-").replace("+00-00", "Z")
        final = runs_dir / f"{self.command}-{ts}.json"
        tmp = final.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        os.replace(tmp, final)
        rotate_artifacts(self.command, runs_dir, keep=ROTATION_KEEP)
        return final


def read_artifact(path: Path) -> RunArtifact:
    """Read and parse a RunArtifact JSON file.

    Args:
        path: Path to the artifact file.

    Returns:
        Parsed :class:`RunArtifact`.

    Raises:
        ArtifactMalformed: when JSON parsing or schema mapping fails (EC-007).
    """
    try:
        raw = path.read_text(encoding="utf-8")
        loaded: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ArtifactMalformed(str(path), f"JSONDecodeError: {exc}") from exc
    except OSError as exc:
        raise ArtifactMalformed(str(path), f"read failed: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ArtifactMalformed(str(path), "top-level JSON must be an object")
    data: dict[str, Any] = {str(k): v for k, v in cast(dict[Any, Any], loaded).items()}

    try:
        fs_raw_any: Any = data.get("fs_observed") or []
        if not isinstance(fs_raw_any, list):
            raise ArtifactMalformed(str(path), "fs_observed must be a list")
        fs_raw = cast(list[Any], fs_raw_any)
        fs_observed: list[FsChange] = []
        for c_any in fs_raw:
            if not isinstance(c_any, dict):
                raise ArtifactMalformed(str(path), "fs_observed entries must be objects")
            c = cast(dict[Any, Any], c_any)
            fs_observed.append(
                FsChange(path=str(c.get("path", "")), change=str(c.get("change", "")))
            )
        return RunArtifact(
            command=str(data["command"]),
            timestamp=str(data["timestamp"]),
            flags=list(cast(list[Any], data.get("flags") or [])),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            exit_code=int(data["exit_code"]),
            duration_ms=int(data.get("duration_ms", 0)),
            cwd=str(data.get("cwd", "")),
            git_state_before=_git_state_from_dict(data.get("git_state_before") or {}),
            git_state_after=_git_state_from_dict(data.get("git_state_after") or {}),
            fs_observed=fs_observed,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ArtifactMalformed(str(path), f"schema error: {exc}") from exc


def find_latest_artifact(command: str, runs_dir: Path) -> Path | None:
    """Return the lexicographically latest artifact for ``command`` (EC-009)."""
    if not runs_dir.exists():
        return None
    candidates = sorted(runs_dir.glob(f"{command}-*.json"))
    if not candidates:
        legacy_command = short_command_name(command)
        if legacy_command != command:
            candidates = sorted(runs_dir.glob(f"{legacy_command}-*.json"))
    return candidates[-1] if candidates else None


def rotate_artifacts(command: str, runs_dir: Path, keep: int = ROTATION_KEEP) -> None:
    """Move artifacts beyond ``keep`` into ``runs_dir/_archive/``."""
    if not runs_dir.exists():
        return
    candidates = sorted(runs_dir.glob(f"{command}-*.json"))
    if len(candidates) <= keep:
        return
    archive = runs_dir / "_archive"
    archive.mkdir(parents=True, exist_ok=True)
    for old in candidates[: len(candidates) - keep]:
        shutil.move(str(old), str(archive / old.name))


# ---------- helpers ----------


def _git_state_from_dict(data: dict[str, Any]) -> GitState:
    return GitState(
        branch=str(data.get("branch", "")),
        head_sha=str(data.get("head_sha", "")),
        dirty=list(data.get("dirty") or []),
    )


def snapshot_git_state(cwd: Path) -> GitState:
    """Best-effort git snapshot. Returns empty fields on any failure."""
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return GitState()
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        sha = ""
    try:
        dirty_out = subprocess.check_output(
            ["git", "-C", str(cwd), "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        dirty = [line[3:].strip() for line in dirty_out.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, OSError):
        dirty = []
    return GitState(branch=branch, head_sha=sha, dirty=dirty)


def utc_iso_timestamp() -> str:
    """Return a UTC ISO 8601 timestamp suitable for artifact filenames."""
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def truncate_stream(s: str, limit: int = MAX_STREAM_BYTES) -> str:
    """Truncate a captured stream to ``limit`` bytes with a clear suffix."""
    if len(s.encode("utf-8")) <= limit:
        return s
    truncated = s.encode("utf-8")[:limit].decode("utf-8", errors="ignore")
    omitted = len(s.encode("utf-8")) - len(truncated.encode("utf-8"))
    return truncated + f"\n[...truncated, {omitted} bytes omitted]"


def record_subprocess(
    command: str,
    argv: list[str],
    *,
    cwd: Path,
    flags: list[str] | None = None,
    runs_dir: Path | None = None,
) -> RunArtifact:
    """Run ``argv`` as a subprocess and write a RunArtifact for it.

    Used by ``livespec run wrap`` to capture an external command's behaviour.

    Args:
        command: Logical command name (e.g. ``"status"``).
        argv: Subprocess command-line (e.g. ``["echo", "hello"]``).
        cwd: Working directory.
        flags: Recorded ``flags`` list. Inferred from ``argv[1:]`` if None.
        runs_dir: Override target directory (defaults to ``cwd/.specs/.runs``).

    Returns:
        The :class:`RunArtifact` that was written.
    """
    flags = flags if flags is not None else [a for a in argv[1:] if a.startswith("--")]
    started = datetime.now(tz=UTC)
    git_before = snapshot_git_state(cwd)
    before_snapshot = _snapshot_paths(cwd)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except FileNotFoundError as exc:
        stdout, stderr, exit_code = "", f"command not found: {exc}", 127
    ended = datetime.now(tz=UTC)
    git_after = snapshot_git_state(cwd)
    fs_changes = _diff_paths(cwd, before_snapshot)

    artifact = RunArtifact(
        command=command,
        timestamp=started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        flags=list(flags),
        stdout=truncate_stream(stdout),
        stderr=truncate_stream(stderr),
        exit_code=exit_code,
        duration_ms=int((ended - started).total_seconds() * 1000),
        cwd=str(cwd),
        git_state_before=git_before,
        git_state_after=git_after,
        fs_observed=fs_changes,
    )
    target = runs_dir or (cwd / ".specs" / ".runs")
    artifact.write(target)
    return artifact


def record_from_streams(
    command: str,
    *,
    cwd: Path,
    flags: list[str],
    stdout: str,
    stderr: str,
    exit_code: int,
    duration_ms: int = 0,
    runs_dir: Path | None = None,
) -> RunArtifact:
    """Write an artifact from already-captured stream data.

    Used by interactive slash-commands invoking ``livespec run record``.
    """
    git = snapshot_git_state(cwd)
    artifact = RunArtifact(
        command=command,
        timestamp=utc_iso_timestamp(),
        flags=list(flags),
        stdout=truncate_stream(stdout),
        stderr=truncate_stream(stderr),
        exit_code=exit_code,
        duration_ms=duration_ms,
        cwd=str(cwd),
        git_state_before=git,
        git_state_after=git,
        fs_observed=[],
    )
    target = runs_dir or (cwd / ".specs" / ".runs")
    artifact.write(target)
    return artifact


def _snapshot_paths(root: Path) -> dict[str, float]:
    """Snapshot mtimes of files under ``root/.specs/`` for diffing."""
    base = root / ".specs"
    if not base.exists():
        return {}
    snap: dict[str, float] = {}
    for p in base.rglob("*"):
        if p.is_file() and ".runs" not in p.parts:
            with suppress(OSError):
                snap[str(p)] = p.stat().st_mtime
    return snap


def _diff_paths(root: Path, before: dict[str, float]) -> list[FsChange]:
    """Compute ``fs_observed`` from a before-snapshot."""
    after = _snapshot_paths(root)
    changes: list[FsChange] = []
    before_keys = set(before)
    after_keys = set(after)
    for path in sorted(after_keys - before_keys):
        changes.append(FsChange(path=path, change="create"))
    for path in sorted(before_keys - after_keys):
        changes.append(FsChange(path=path, change="delete"))
    for path in sorted(before_keys & after_keys):
        if after[path] != before[path]:
            changes.append(FsChange(path=path, change="modify"))
    return changes


__all__ = [
    "MAX_STREAM_BYTES",
    "ROTATION_KEEP",
    "FsChange",
    "GitState",
    "RunArtifact",
    "find_latest_artifact",
    "read_artifact",
    "record_from_streams",
    "record_subprocess",
    "rotate_artifacts",
    "snapshot_git_state",
    "truncate_stream",
    "utc_iso_timestamp",
]

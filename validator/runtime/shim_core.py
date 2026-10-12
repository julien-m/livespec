# LiveSpec runtime shim core — standard library only.
# @spec FR-004: Shim resolution and exit 3
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-004
"""Resolve and execute the LiveSpec runtime selected by the current project.

This module is embedded verbatim into ``<home>/bin/livespec`` by
``validator/runtime/shim.py`` and must therefore only import the standard
library. Per invocation it reads at most the project-root lock and one snapshot
manifest (plus the ``current`` target on the runtime-subcommand fallback); it
never recomputes a content digest. It is also imported by the runtime commands
for the strict lock parser and the root predicates, so both share one contract.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple, cast

SHIM_PREFIX = "livespec-shim:"
WARNING_PREFIX = "livespec-shim-warning:"
NOTICE_PREFIX = "livespec-shim-notice:"
# Constitution exit code reserved for shim resolution failures; the stderr prefix
# distinguishes them from a runtime that itself exits 3.
SHIM_EXIT_CODE = 3
HOME_ENV = "LIVESPEC_HOME"
LOCK_NAME = "livespec.lock"
MANIFEST_FILE = ".livespec-runtime.json"
LOCK_SCHEMA = 1
PINNED_KEYS = frozenset({"commit", "livespec_version", "mode", "runtime_id", "schema"})
DEV_KEYS = frozenset({"mode", "schema", "source"})
# Runtime id "<VERSION>-<first 12 hex chars of the commit>", e.g. "21-0123456789ab".
RUNTIME_ID_RE = re.compile(r"\A[0-9]+-[0-9a-f]{12}\Z")
# Full commit hash: 40 hex (SHA-1 repositories) or 64 hex (SHA-256 repositories).
COMMIT_RE = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
# Manifest shape checked by the shim without importing validator (mirrors models.MANIFEST_KEYS).
MANIFEST_SHAPE_KEYS = frozenset(
    {"schema", "runtime_id", "livespec_version", "commit", "source", "created_at", "content_digest"}
)
# Content digest format "sha256:<64 hex>"; the shim never recomputes it (FR-004).
DIGEST_RE = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
CHECKOUT_INSTALL = "python3 -m validator.cli runtime install"

LockData = dict[str, str | int]


class ShimResolutionError(Exception):
    """Raised when no runtime can be resolved for the invocation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Resolution(NamedTuple):
    """Runtime root selected for execution plus stderr notices to print first."""

    root: Path
    messages: tuple[str, ...] = ()


def find_project_root(start: Path) -> Path | None:
    """Return the nearest ancestor of ``start`` (inclusive) holding a ``.specs/`` directory."""
    current = start.expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".specs").is_dir():
            return candidate
    return None


def is_livespec_root(path: Path) -> bool:
    """Return whether ``path`` holds ``VERSION``, ``validator/`` and ``.agent-sync/``."""
    return (
        (path / "VERSION").is_file()
        and (path / "validator").is_dir()
        and (path / ".agent-sync").is_dir()
    )


def _invalid(path: Path, reason: str) -> ShimResolutionError:
    return ShimResolutionError(
        f"invalid runtime lock {path}: {reason}; "
        "rewrite it with `livespec runtime pin` or `livespec runtime dev`"
    )


def _check_pinned(data: dict[str, object], path: Path) -> LockData:
    runtime_id, commit, version = data["runtime_id"], data["commit"], data["livespec_version"]
    if not isinstance(runtime_id, str) or not RUNTIME_ID_RE.match(runtime_id):
        raise _invalid(path, "runtime_id must look like <VERSION>-<sha12>")
    if not isinstance(commit, str) or not COMMIT_RE.match(commit):
        raise _invalid(path, "commit must be a full hexadecimal hash")
    if type(version) is not int or runtime_id != f"{version}-{commit[:12]}":
        raise _invalid(path, "livespec_version and commit do not match runtime_id")
    return {
        "schema": LOCK_SCHEMA,
        "mode": "pinned",
        "runtime_id": runtime_id,
        "livespec_version": version,
        "commit": commit,
    }


def parse_lock(text: str, path: Path) -> LockData:
    """Parse ``.specs/livespec.lock`` strictly (schema 1, mode pinned or dev, exact keys).

    Args:
        text: Raw lock file content.
        path: Lock path named in error messages.

    Returns:
        The validated lock mapping.

    Raises:
        ShimResolutionError: If the lock is not valid JSON or violates schema 1.
    """
    try:
        raw: object = json.loads(text)
    except ValueError as exc:
        raise _invalid(path, "not valid JSON") from exc
    if not isinstance(raw, dict):
        raise _invalid(path, "not a JSON object")
    # json.loads returns untyped dicts whose keys are JSON strings; values are checked below.
    data = cast("dict[str, object]", raw)
    if data.get("schema") != LOCK_SCHEMA or type(data.get("schema")) is not int:
        raise _invalid(path, "unknown schema")
    mode = data.get("mode")
    if mode == "pinned" and frozenset(data) == PINNED_KEYS:
        return _check_pinned(data, path)
    source = data.get("source")
    if mode == "dev" and frozenset(data) == DEV_KEYS and isinstance(source, str) and source:
        return {"schema": LOCK_SCHEMA, "mode": "dev", "source": source}
    raise _invalid(path, "unknown mode or unexpected keys")


def dev_source_root(project: Path, source: str) -> Path:
    """Resolve a dev lock source, relative paths being relative to the project root."""
    candidate = Path(source).expanduser()
    return (candidate if candidate.is_absolute() else project / candidate).resolve()


def _pinned_root(home: Path, lock: LockData) -> Path:
    runtime_id, commit = str(lock["runtime_id"]), str(lock["commit"])
    snapshot = home / "versions" / runtime_id
    recovery = f"livespec runtime install --source <livespec repo> --ref {commit}"
    if not (home / "current").is_dir():
        recovery += (
            f" (no current runtime: run `{CHECKOUT_INSTALL} --ref {commit}` in the checkout)"
        )
    try:
        manifest: object = json.loads((snapshot / MANIFEST_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ShimResolutionError(
            f"pinned runtime {runtime_id} is not installed under {home / 'versions'}; "
            f"recover with `{recovery}`"
        ) from exc
    identity = cast("dict[str, object]", manifest) if isinstance(manifest, dict) else {}
    if identity.get("runtime_id") != runtime_id or identity.get("commit") != commit:
        raise ShimResolutionError(
            f"runtime {runtime_id} manifest does not match the lock commit {commit}; "
            f"recover with `{recovery}`"
        )
    return snapshot


def _project_resolution(project: Path, home: Path) -> Resolution:
    lock_path = project / ".specs" / LOCK_NAME
    try:
        text = lock_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _invalid(lock_path, "unreadable") from exc
    lock = parse_lock(text, lock_path)
    if lock["mode"] == "pinned":
        return Resolution(_pinned_root(home, lock))
    root = dev_source_root(project, str(lock["source"]))
    if not is_livespec_root(root):
        raise ShimResolutionError(f"dev source in {lock_path} is not a LiveSpec root: {root}")
    if root == project:
        return Resolution(root)
    return Resolution(root, (f"{NOTICE_PREFIX} dev mode executes the LiveSpec checkout {root}",))


def _is_utc_timestamp(value: str) -> bool:
    """Return whether ``value`` is an ISO-8601 timestamp with a zero UTC offset."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.utcoffset() == timedelta(0)


def _manifest_identity_ok(identity: dict[str, object], directory: Path) -> bool:
    runtime_id, commit = identity.get("runtime_id"), identity.get("commit")
    version = identity.get("livespec_version")
    schema, digest = identity.get("schema"), identity.get("content_digest")
    source, created_at = identity.get("source"), identity.get("created_at")
    return (
        frozenset(identity) == MANIFEST_SHAPE_KEYS
        and isinstance(source, str)
        and Path(source).is_absolute()
        and isinstance(created_at, str)
        and _is_utc_timestamp(created_at)
        and type(schema) is int
        and schema == LOCK_SCHEMA
        and isinstance(digest, str)
        and bool(DIGEST_RE.match(digest))
        and isinstance(runtime_id, str)
        and isinstance(commit, str)
        and type(version) is int
        and runtime_id == directory.name
        and bool(RUNTIME_ID_RE.match(runtime_id) and COMMIT_RE.match(commit))
        and runtime_id == f"{version}-{commit[:12]}"
    )


# @spec FR-004: Current must be a verified snapshot
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-004
def _current_snapshot(home: Path) -> Path:
    """Return ``<home>/current``'s snapshot after one manifest identity read (no digest)."""
    current = home / "current"
    missing = ShimResolutionError(
        f"no runtime installed under {home}; install one from the LiveSpec checkout with "
        f"its own CLI: `cd <livespec repo> && {CHECKOUT_INSTALL}`"
    )
    try:
        target = current.resolve(strict=True)
        installed = target.parent == (home / "versions").resolve() and is_livespec_root(target)
        is_directory = current.is_dir()
    except (OSError, RuntimeError) as exc:
        # A dangling, looping or unreadable `current` is an absent runtime, not a crash.
        raise missing from exc
    if not is_directory:
        raise missing
    try:
        manifest: object = json.loads((target / MANIFEST_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = None
    identity = cast("dict[str, object]", manifest) if isinstance(manifest, dict) else {}
    if not (installed and _manifest_identity_ok(identity, target)):
        raise ShimResolutionError(
            f"{current} does not point to an installed runtime snapshot ({target}); "
            f"reinstall from the LiveSpec checkout: `cd <livespec repo> && {CHECKOUT_INSTALL}`"
        )
    return target


def resolve_runtime(cwd: Path, home: Path, argv: list[str]) -> Resolution:
    """Select the runtime root for one shim invocation.

    Args:
        cwd: Working directory of the invocation.
        home: Runtime home (``$LIVESPEC_HOME`` or the generated home).
        argv: CLI arguments after the program name.

    Returns:
        The runtime root and notices; ``runtime`` subcommands fall back to ``current``.

    Raises:
        ShimResolutionError: If resolution fails and no fallback applies.
    """
    project = find_project_root(cwd)
    try:
        if project is not None and (project / ".specs" / LOCK_NAME).exists():
            return _project_resolution(project, home)
        return Resolution(_current_snapshot(home))
    except ShimResolutionError as exc:
        # Only recovery/inspection (`livespec runtime ...`) may run on another runtime,
        # and only on a verified installed snapshot (the one extra manifest read).
        if argv[:1] != ["runtime"]:
            raise
        try:
            fallback = _current_snapshot(home)
        except ShimResolutionError:
            raise exc from None
        warning = f"{WARNING_PREFIX} {exc.message}; dispatching to {fallback}"
        return Resolution(fallback, (warning,))


def run_runtime(root: Path, argv: list[str]) -> int:
    """Execute ``validator.cli`` from ``root`` in this interpreter.

    Side effects: disables bytecode writing, puts ``root`` first on ``sys.path``
    and purges already imported ``validator`` modules so an editable install of
    another checkout cannot shadow the selected runtime.

    Args:
        root: Selected LiveSpec root.
        argv: Arguments passed unchanged to the runtime CLI.

    Returns:
        0 when the CLI returns without raising ``SystemExit`` (Typer normally raises).
    """
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    for name in [key for key in sys.modules if key == "validator" or key.startswith("validator.")]:
        del sys.modules[name]
    sys.argv = ["livespec", *argv]
    app = cast("Callable[[], object]", importlib.import_module("validator.cli").app)
    app()
    return 0


def main(generated_home: str) -> int:
    """Shim entry point: resolve, report notices, export the home and run the runtime.

    Args:
        generated_home: Home recorded when the shim was generated.

    Returns:
        ``SHIM_EXIT_CODE`` on a resolution failure, else the runtime result.
    """
    home = Path(os.environ.get(HOME_ENV) or generated_home).expanduser()
    argv = sys.argv[1:]
    try:
        resolution = resolve_runtime(Path.cwd(), home, argv)
    except ShimResolutionError as exc:
        sys.stderr.write(f"{SHIM_PREFIX} {exc.message}\n")
        return SHIM_EXIT_CODE
    for message in resolution.messages:
        sys.stderr.write(f"{message}\n")
    os.environ.setdefault(HOME_ENV, str(home))
    return run_runtime(resolution.root, argv)

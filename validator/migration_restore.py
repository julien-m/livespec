"""Capture and replay scoped migration pre-images using schema-1 restore points."""

# @spec FR-004: Preserve migration pre-images and perform explicit rollback
#   — .specs/features/122-review-led-delivery/spec.md#fr-004

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

STORE_RELPATH = PurePosixPath(".specs/.migration-restore")
VERSION_RELPATH = PurePosixPath(".specs/livespec-version")
SCHEMA = 1
MANIFEST_NAME = "manifest.json"
BLOBS_NAME = "blobs"
KIND_FILE = "file"
KIND_LINK = "symlink"
KIND_DIRECTORY = "directory"
KINDS = {KIND_FILE: stat.S_ISREG, KIND_LINK: stat.S_ISLNK, KIND_DIRECTORY: stat.S_ISDIR}
_SHA256 = re.compile(r"[a-f0-9]{64}")
_STORE_IGNORE = b"# LiveSpec migration restore store.\n/*\n"
V22_SCOPE = (
    ".agent-sync",
    ".agent-sync.local",
    ".agents",
    ".claude",
    ".codex",
    ".gitignore",
    ".ruff_cache",
    ".specs/conventions",
    ".specs/conventions-gates.yaml",
    ".specs/conventions-rulebook.yaml",
    ".specs/livespec-version",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    ".eslintrc.json",
    ".swiftlint.yml",
)
V22_LEGACY_SCOPE = (
    ".agent-sync",
    ".agent-sync.local",
    ".agents",
    ".claude",
    ".codex",
    ".conventions",
    ".eslintrc.json",
    ".ruff_cache",
    ".specs",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
)
V23_SCOPE = (".gitignore", ".specs/livespec-version", ".specs/recovery-policy.yaml")
_SUPPORTED_SCOPES = {22: (V22_SCOPE, V22_LEGACY_SCOPE), 23: (V23_SCOPE,)}


class RestorePointError(Exception):
    """Invalid restore point or unsafe migration destination."""


@dataclass(frozen=True)
class Entry:
    """One recorded path of the scope."""

    path: str
    kind: str
    mode: int
    digest: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class Outcome:
    """The disposition of the backup and the number of affected entries."""

    status: str
    entries: int
    removed: int = 0


def store_of(project: Path, version: int) -> Path:
    """Return the directory holding the restore point of migration ``version``."""
    return project.joinpath(*STORE_RELPATH.parts, str(version))


def _relative(raw: object) -> PurePosixPath:
    if not isinstance(raw, str):
        raise RestorePointError("restore path must be a string")
    relative = PurePosixPath(raw)
    if (
        not relative.parts
        or relative.is_absolute()
        or ".." in relative.parts
        or ".git" in (part.casefold() for part in relative.parts)
        or any(character in raw for character in ("\\", ":", "\0"))
        or str(relative) != raw
        or _is_store(relative)
    ):
        raise RestorePointError(f"unsafe relative restore path: {raw!r}")
    return relative


def _is_store(relative: PurePosixPath) -> bool:
    store = STORE_RELPATH.parts
    return tuple(part.casefold() for part in relative.parts[: len(store)]) == store


def _kind(path: Path) -> int | None:
    try:
        return os.lstat(path).st_mode
    except FileNotFoundError:
        return None


def _check_directories(project: Path, target: Path) -> None:
    """Refuse redirects and non-directory ancestors even when a leaf is missing."""
    for relative in reversed(target.relative_to(project).parents):
        ancestor = project / relative
        mode = _kind(ancestor)
        if mode is not None and not stat.S_ISDIR(mode):
            raise RestorePointError(f"{ancestor} must be a real directory")


def _checked_store(project: Path, version: int) -> Path:
    store = store_of(project, version)
    _check_directories(project, store / BLOBS_NAME / "placeholder")
    return store


def _checked_scope(project: Path, scope: Sequence[object]) -> tuple[PurePosixPath, ...]:
    if not scope:
        raise RestorePointError("a restore point needs at least one scope path")
    roots = tuple(sorted(_relative(raw) for raw in scope))
    folded = tuple(PurePosixPath(root.as_posix().casefold()) for root in roots)
    for position, root in enumerate(roots):
        _check_directories(project, project / root)
        if any(
            other == folded[position]
            or other in folded[position].parents
            or folded[position] in other.parents
            for index, other in enumerate(folded)
            if index != position
        ):
            raise RestorePointError(f"overlapping restore scope: {root}")
    return roots


def _validate_migration_scope(version: int, roots: Sequence[PurePosixPath]) -> None:
    names = {str(root) for root in roots}
    if not any(names == set(scope) for scope in _SUPPORTED_SCOPES.get(version, ())):
        raise RestorePointError(f"restore scope does not match migration {version}")


def _walk(project: Path, roots: Sequence[PurePosixPath]) -> Iterator[tuple[PurePosixPath, int]]:
    for root in roots:
        pending = [root]
        while pending:
            relative = pending.pop()
            if _is_store(relative):
                continue
            # Store links as links: a directory redirect may point outside the project.
            mode = _kind(project / relative)
            if mode is not None:
                yield relative, mode
                if stat.S_ISDIR(mode):
                    children = sorted(os.listdir(project / relative), reverse=True)
                    pending.extend(relative / name for name in children)


def _digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _capture(project: Path, store: Path, relative: PurePosixPath, mode: int) -> Entry:
    name = str(_relative(str(relative)))
    permissions = stat.S_IMODE(mode)
    path = project / relative
    if stat.S_ISLNK(mode):
        return Entry(name, KIND_LINK, permissions, target=os.readlink(path))
    if stat.S_ISDIR(mode):
        return Entry(name, KIND_DIRECTORY, permissions)
    if not stat.S_ISREG(mode):
        raise RestorePointError(f"unsupported pre-image kind: {relative}")
    temporary = store / "capture"
    shutil.copyfile(path, temporary)
    digest = _digest(temporary)
    blob = store / BLOBS_NAME / digest
    if blob.exists():
        temporary.unlink()
    else:
        temporary.replace(blob)
    return Entry(name, KIND_FILE, permissions, digest=digest)


def _project_version(project: Path) -> str | None:
    path = project / VERSION_RELPATH
    mode = _kind(path)
    if mode is None:
        return None
    if not stat.S_ISREG(mode):
        raise RestorePointError(f"{path} must be a regular file")
    return path.read_text(encoding="utf-8").strip()


def _protect_store(parent: Path) -> None:
    parent.mkdir(exist_ok=True)
    marker = parent / ".gitignore"
    try:
        with marker.open("xb") as file:
            file.write(_STORE_IGNORE)
    except FileExistsError as error:
        mode = _kind(marker)
        if mode is None or not stat.S_ISREG(mode) or marker.read_bytes() != _STORE_IGNORE:
            raise RestorePointError(f"refusing to replace custom ignore file: {marker}") from error


def record(project: Path, version: int, scope: Sequence[str]) -> Outcome:
    """Record the project state before migration, keeping the first complete backup."""
    roots = _checked_scope(project, scope)
    _validate_migration_scope(version, roots)
    store = _checked_store(project, version)
    project_version = _project_version(project)
    if store.exists():
        if project_version not in (str(version - 1), str(version)):
            raise RestorePointError(
                f"project version {project_version} cannot run migration {version}"
            )
        kept = _keep_point(project, store, version, roots)
        _protect_store(store.parent)
        return kept
    if project_version != str(version - 1):
        raise RestorePointError(
            f"migration {version} needs project version {version - 1}, found {project_version}"
        )

    # Staged bytes and the complete backup are ignored even before the root ignore is updated.
    _protect_store(store.parent)
    # Publish the completed backup as one directory so interrupted retries retain the pre-image.
    with tempfile.TemporaryDirectory(dir=store.parent, prefix=f".{version}-") as scratch:
        staged = Path(scratch) / "point"
        (staged / BLOBS_NAME).mkdir(parents=True)
        entries = [_capture(project, staged, rel, mode) for rel, mode in _walk(project, roots)]
        document = {
            "schema": SCHEMA,
            "migration": version,
            "project_version": project_version,
            "scope": [str(root) for root in roots],
            "entries": [asdict(entry) for entry in entries],
        }
        (staged / MANIFEST_NAME).write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if store.exists():
            return _keep_point(project, store, version, roots)
        staged.rename(store)
    return Outcome("recorded", len(entries))


def _keep_point(
    project: Path, store: Path, version: int, requested: Sequence[PurePosixPath]
) -> Outcome:
    scope, entries = _load_point(project, store, version)
    if any(root not in scope and not set(root.parents).intersection(scope) for root in requested):
        raise RestorePointError(
            "first restore point does not cover this migration's writes; "
            "use the runtime that recorded it to resume or roll back"
        )
    return Outcome("kept", len(entries))


def _manifest(store: Path, version: int) -> dict[str, object]:
    path = store / MANIFEST_NAME
    mode = _kind(path)
    if mode is None:
        raise RestorePointError(f"no restore point for migration {version}: {path} is missing")
    if not stat.S_ISREG(mode):
        raise RestorePointError(f"{path} must be a regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise RestorePointError(f"{path} is not valid JSON") from error
    if (
        not isinstance(document, dict)
        or type(document.get("schema")) is not int
        or document["schema"] != SCHEMA
        or type(document.get("migration")) is not int
        or document.get("migration") != version
        or document.get("project_version") != str(version - 1)
    ):
        raise RestorePointError(f"{path}: invalid schema or migration version")
    return document


def _entry(item: object) -> Entry:
    if not isinstance(item, dict):
        raise RestorePointError("invalid restore entry")
    path = str(_relative(item.get("path")))
    kind = item.get("kind")
    mode = item.get("mode")
    digest = item.get("digest")
    target = item.get("target")
    if (
        not isinstance(kind, str)
        or kind not in KINDS
        or type(mode) is not int
        or not 0 <= mode <= 0o7777
    ):
        raise RestorePointError(f"invalid kind or permissions for pre-image of {path}")
    if kind == KIND_FILE:
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest) or target is not None:
            raise RestorePointError(f"invalid digest for pre-image of {path}")
    elif (
        digest is not None
        or (kind == KIND_LINK and (not isinstance(target, str) or not target or "\0" in target))
        or (kind == KIND_DIRECTORY and target is not None)
    ):
        raise RestorePointError(f"invalid target or digest for pre-image of {path}")
    return Entry(path, kind, mode, digest, target)


def _load_point(
    project: Path, store: Path, version: int
) -> tuple[tuple[PurePosixPath, ...], list[Entry]]:
    document = _manifest(store, version)
    scope = document.get("scope")
    items = document.get("entries")
    if not isinstance(scope, list) or not isinstance(items, list):
        raise RestorePointError(f"{store / MANIFEST_NAME}: expected scope and entries arrays")
    roots = _checked_scope(project, scope)
    _validate_migration_scope(version, roots)
    entries: dict[PurePosixPath, Entry] = {}
    names: set[str] = set()
    verified: set[str] = set()
    for item in items:
        entry = _entry(item)
        relative = PurePosixPath(entry.path)
        if relative not in roots:
            parent = entries.get(relative.parent)
            if parent is None or parent.kind != KIND_DIRECTORY:
                raise RestorePointError(
                    f"pre-image path {relative} is outside scope or out of order"
                )
        name = entry.path.casefold()
        if name in names:
            raise RestorePointError(f"duplicate pre-image path {relative}")
        names.add(name)
        entries[relative] = entry
        digest = entry.digest
        if digest is not None and digest not in verified:
            blob = store / BLOBS_NAME / digest
            mode = _kind(blob)
            if mode is None or not stat.S_ISREG(mode) or _digest(blob) != digest:
                raise RestorePointError(f"pre-image of {entry.path} is missing or altered")
            verified.add(digest)
    version_entry = entries.get(VERSION_RELPATH)
    if version_entry is None or version_entry.digest is None:
        raise RestorePointError("restore point is missing the project version pre-image")
    version_blob = store / BLOBS_NAME / version_entry.digest
    if version_blob.read_text(encoding="utf-8").strip() != document["project_version"]:
        raise RestorePointError("restore point project version does not match its pre-image")
    return roots, list(entries.values())


def _writable(directory: Path) -> None:
    mode = stat.S_IMODE(os.lstat(directory).st_mode)
    if mode & stat.S_IRWXU != stat.S_IRWXU:
        directory.chmod(mode | stat.S_IRWXU)


def _prepare_paths(project: Path, roots: Sequence[PurePosixPath], entries: Sequence[Entry]) -> int:
    current = list(_walk(project, roots))
    expected = {entry.path: entry.kind for entry in entries}
    # Writable directories inside the restoration scope may have been generated read-only.
    for relative, mode in current:
        if stat.S_ISDIR(mode):
            _writable(project / relative)
    removed = 0
    for relative, mode in reversed(current):
        kind = expected.get(str(relative))
        if kind is None or not KINDS[kind](mode):
            (project / relative).rmdir() if stat.S_ISDIR(mode) else (project / relative).unlink()
            removed += 1
    return removed


def _put(project: Path, store: Path, entry: Entry) -> None:
    path = project / entry.path
    if entry.kind == KIND_DIRECTORY:
        path.mkdir(exist_ok=True)
        _writable(path)
        return
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".livespec-restore-") as scratch:
        temporary = Path(scratch) / "entry"
        if entry.target is not None:
            temporary.symlink_to(entry.target)
        elif entry.digest is not None:
            shutil.copyfile(store / BLOBS_NAME / entry.digest, temporary)
            temporary.chmod(entry.mode)
        temporary.replace(path)


def _discard_point(store: Path) -> None:
    shutil.rmtree(store)
    parent = store.parent
    # A legacy restore may have reset .specs to a read-only mode. In that case
    # leave the administrative directory and its ignore file in place.
    if not (parent.parent.stat().st_mode & stat.S_IWUSR):
        return
    marker = parent / ".gitignore"
    if set(parent.iterdir()) == {marker}:
        mode = _kind(marker)
        if mode is not None and stat.S_ISREG(mode) and marker.read_bytes() == _STORE_IGNORE:
            marker.unlink()
    if not any(parent.iterdir()):
        parent.rmdir()


def restore(project: Path, version: int) -> Outcome:
    """Verify all pre-images, restore the migration's scope and remove the backup."""
    store = _checked_store(project, version)
    current = _project_version(project)
    if current not in (str(version), str(version - 1)):
        raise RestorePointError(
            f"project version is {current}; run the inverses of migrations above {version} first"
        )
    roots, entries = _load_point(project, store, version)
    removed = _prepare_paths(project, roots, entries)
    for entry in entries:
        _put(project, store, entry)
    for entry in reversed(entries):
        if entry.kind == KIND_DIRECTORY:
            (project / entry.path).chmod(entry.mode)
    _discard_point(store)
    return Outcome("restored", len(entries), removed)

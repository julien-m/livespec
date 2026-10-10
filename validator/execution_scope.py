"""Conservative execution input manifests and no-follow evidence reads."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .normative_identity import normative_hash

# Generated caches and runner-owned results are not application inputs. Every
# other regular file, including configuration and shared sources, is hashed.
_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".pyright",
    }
)
_EXCLUDED_PREFIXES = (
    ".specs/.runs/",
    ".specs/.execution/",
    ".specs/conventions/runs/",
    ".worktrees/",
)
_LINK = re.compile(r"\[[^\]]*\]\(<?([^\s)>]+)>?(?:\s+[^)]*)?\)")
_EXCLUDED_FILES = frozenset({".coverage", ".DS_Store"})
EXECUTION_SCOPE_POLICY = "078.1"
_GENERATED_REGISTRIES = frozenset({".specs/README.md", ".specs/changelog.md", ".specs/roadmap.md"})
_GENERATED_FEATURE_FILES = frozenset(
    {"pipeline.md", "progress.md", "changelog.md", "implementation.md"}
)


def digest(data: bytes) -> str:
    """Return the SHA-256 identity of exact bytes."""
    return hashlib.sha256(data).hexdigest()


def read_regular(path: Path, root: Path) -> bytes:
    """Read a confined regular file without following any symlink component."""
    relative = path.absolute().relative_to(root.absolute())
    if ".." in relative.parts:
        raise ValueError("Evidence cannot traverse outside its confined root")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return read_from_directory(directory, relative.name)
    finally:
        os.close(directory)


def read_from_directory(directory_fd: int, name: str) -> bytes:
    """Read stable regular bytes relative to an already pinned parent descriptor."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Evidence must be a regular file")
        content = stream.read()
        after = os.fstat(stream.fileno())
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)

        def identity(value: os.stat_result) -> tuple[int, int, int, int]:
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns

        if identity(before) != identity(after) or identity(after) != identity(current):
            raise ValueError("Evidence changed while reading")
        return content


def source_manifest(project_root: Path, feature: str | None = None) -> dict[str, str]:
    """Hash conservative inputs; optionally normalize selected lifecycle metadata only."""
    root = project_root.resolve(strict=True)
    result: dict[str, str] = {}
    lifecycle = {f".specs/features/{feature}/{name}" for name in ("spec.md", "plan.md")}
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        dirs[:] = sorted(name for name in dirs if not _excluded(base / name, root, feature))
        for name in dirs:
            path = base / name
            if path.is_symlink():
                _symlink_identity(path, root, result)
        for name in sorted(files):
            path = base / name
            if _excluded(path, root, feature):
                continue
            relative = path.relative_to(root).as_posix()
            target = _symlink_identity(path, root, result) if path.is_symlink() else path
            data = read_regular(target, root)
            result[relative] = (
                normative_hash(data.decode(), lifecycle_document=True)
                if feature and relative in lifecycle
                else digest(data)
            )
    if feature:
        result.update(_referenced_inputs(root, feature))
    return result


def _referenced_inputs(root: Path, feature: str) -> dict[str, str]:
    """Explicit referenced inputs override generated-result exclusions."""
    pending = [root / ".specs/features" / feature / name for name in ("spec.md", "plan.md")]
    seen: set[Path] = set()
    included: dict[str, str] = {}
    while pending:
        document = pending.pop()
        if document in seen or not document.is_file():
            continue
        seen.add(document)
        if len(seen) > 128:
            raise ValueError("Referenced execution input inventory exceeds 128 documents")
        content = read_regular(document, root).decode()
        for match in _LINK.finditer(content):
            target = urlsplit(unquote(match.group(1)))
            if target.scheme or target.netloc or not target.path:
                continue
            path = (document.parent / target.path).resolve(strict=True)
            relative = path.relative_to(root).as_posix()
            if not path.is_file():
                continue
            if any(
                _excluded(parent, root, feature)
                for parent in (path, *path.parents)
                if parent != root and root in parent.parents
            ):
                included[relative] = digest(read_regular(path, root))
            if path.suffix == ".md":
                pending.append(path)
    return included


def _excluded(path: Path, root: Path, feature: str | None = None) -> bool:
    relative = path.relative_to(root).as_posix()
    feature_root = f".specs/features/{feature}/"
    generated_feature = bool(
        feature
        and relative.startswith(feature_root)
        and (
            relative.removeprefix(feature_root) in _GENERATED_FEATURE_FILES
            or relative.removeprefix(feature_root) in {".reviews", "run"}
            or relative.removeprefix(feature_root).startswith((".reviews/", "run/"))
        )
    )
    return (
        relative in _GENERATED_REGISTRIES
        or generated_feature
        or path.name in _EXCLUDED_DIRS
        or path.name in _EXCLUDED_FILES
        or any(
            relative == prefix.rstrip("/") or relative.startswith(prefix)
            for prefix in _EXCLUDED_PREFIXES
        )
    )


def _symlink_identity(path: Path, root: Path, result: dict[str, str]) -> Path:
    # Internal provider links retain their link identity and refer to canonical
    # files already in the enumerated scope. External or excluded targets cannot
    # establish a complete local source snapshot.
    target = path.resolve(strict=True)
    target.relative_to(root)
    if any(
        _excluded(parent, root)
        for parent in (target, *target.parents)
        if parent != root and root in parent.parents
    ):
        raise ValueError(f"Execution source symlink targets excluded inputs: {path}")
    result[path.relative_to(root).as_posix() + "@symlink"] = digest(os.readlink(path).encode())
    return target

# @spec(FR-006)

# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)

"""Feature-scope resolver for deterministic conventions verification."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

SOURCE_SUFFIXES = frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".swift", ".css"})
_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")
_MARKDOWN_CODE_PATH_PATTERN = re.compile(r"`(?P<target>[^`]+)`")
_DATE_PATTERN = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")


class FeatureScopeError(ValueError):
    """Raised when a requested feature scope cannot be resolved."""


@dataclass(frozen=True)
class FeatureScope:
    """Feature-owned source paths used by scoped conventions verification."""

    feature_slug: str
    paths: frozenset[str]


def resolve_feature_scope(project_root: Path, feature_slug: str) -> FeatureScope:
    """Resolve current source/test files attributable to a LiveSpec feature."""
    feature_dir = project_root / ".specs" / "features" / feature_slug
    if not feature_dir.is_dir():
        raise FeatureScopeError(f"feature scope not found: .specs/features/{feature_slug}")
    implementation = feature_dir / "implementation.md"
    if not implementation.is_file():
        raise FeatureScopeError(f"feature scope missing implementation.md: {implementation}")
    try:
        implementation_text = implementation.read_text(encoding="utf-8")
    except OSError as exc:
        raise FeatureScopeError(f"feature scope unreadable: {implementation}") from exc
    paths = frozenset(
        _feature_scope_paths(project_root, feature_dir, implementation, implementation_text)
    )
    if not paths:
        raise FeatureScopeError(f"feature scope has no mapped source files: {implementation}")
    return FeatureScope(feature_slug=feature_slug, paths=paths)


def _feature_scope_paths(
    project_root: Path,
    feature_dir: Path,
    implementation: Path,
    implementation_text: str,
) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    _append_scope_paths(
        paths,
        seen,
        _artifact_scope_paths(
            project_root, implementation, _current_mapping_text(implementation_text)
        ),
    )
    _append_scope_paths(paths, seen, _dirty_feature_scope_paths(project_root, feature_dir.name))
    return paths


def _current_mapping_text(implementation_text: str) -> str:
    dated_lines = [
        (match.group(0), line)
        for line in implementation_text.splitlines()
        if (match := _DATE_PATTERN.search(line)) is not None
    ]
    if not dated_lines:
        return implementation_text
    latest = max(date for date, _line in dated_lines)
    return "\n".join(line for date, line in dated_lines if date == latest)


def _append_scope_paths(paths: list[str], seen: set[str], candidates: list[str]) -> None:
    for rel in candidates:
        if rel not in seen:
            paths.append(rel)
            seen.add(rel)


def _artifact_scope_paths(project_root: Path, artifact: Path, text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for target in _markdown_path_targets(text):
        for candidate in _scope_path_candidates(project_root, artifact, target):
            try:
                rel = candidate.relative_to(project_root.resolve()).as_posix()
            except ValueError:
                continue
            if (
                candidate.is_file()
                and candidate.suffix.lower() in SOURCE_SUFFIXES
                and rel not in seen
            ):
                paths.append(rel)
                seen.add(rel)
    return paths


def _markdown_path_targets(text: str) -> list[str]:
    targets: list[str] = []
    for pattern in (_MARKDOWN_LINK_PATTERN, _MARKDOWN_CODE_PATH_PATTERN):
        targets.extend(match.group("target") for match in pattern.finditer(text))
    return targets


def _scope_path_candidates(project_root: Path, artifact: Path, target: str) -> list[Path]:
    cleaned = target.split("#", 1)[0].strip()
    if not cleaned or "://" in cleaned or "*" in cleaned or "\n" in cleaned or "\r" in cleaned:
        return []
    target_path = Path(cleaned)
    if target_path.is_absolute():
        return [target_path.resolve()]
    return [(artifact.parent / target_path).resolve(), (project_root / target_path).resolve()]


def _dirty_feature_scope_paths(project_root: Path, feature_slug: str) -> list[str]:
    changed_paths = _git_changed_paths(project_root)
    feature_prefix = f".specs/features/{feature_slug}/"
    if not any(path.startswith(feature_prefix) for path in changed_paths):
        return []
    return [
        path
        for path in changed_paths
        if Path(path).suffix.lower() in SOURCE_SUFFIXES and (project_root / path).is_file()
    ]


def _git_changed_paths(project_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), "status", "--porcelain=v1", "--untracked-files=all"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.rsplit(" -> ", 1)[1]
        if rel:
            paths.append(rel)
    return paths

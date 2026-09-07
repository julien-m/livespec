"""Load canonical local review inputs without silently losing references (078 FR-002)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, cast
from urllib.parse import unquote, urlsplit

from .config import load_semantic_config
from .review_context import PreparedReview, content_hash, prepare_review_context

_LINK = re.compile(r"\[[^\]]*\]\(<?([^\s)>]+)>?(?:\s+[^)]*)?\)")
_MAX_SOURCES = 128


def current_review_model(project_root: Path, model: str = "") -> str:
    """Resolve the configured model; an unresolved provider default stays explicit."""
    if model:
        return model
    config = load_semantic_config(project_root / ".specs")
    return config.review_model or next(iter(config.review_reviewers), "")


def review_receipt_path(project_root: Path, feature: str, kind: str) -> Path:
    """Return the existing feature run location for a disposable review receipt."""
    return project_root / ".specs" / "features" / feature / ".reviews" / f"{kind}.json"


def _references(path: Path, text: str, project_root: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    errors: list[str] = []
    for match in _LINK.finditer(text):
        target = unquote(match.group(1))
        parsed = urlsplit(target)
        if not parsed.path.endswith(".md"):
            continue
        if parsed.scheme or parsed.netloc:
            errors.append(f"external_contract_not_loaded:{target}")
            continue
        candidate = (path.parent / parsed.path).resolve()
        try:
            candidate.relative_to(project_root)
        except ValueError:
            errors.append(f"contract_outside_project:{target}")
            continue
        if candidate != path:
            paths.append(candidate)
    return paths, errors


def prepare_feature_review(
    project_root: Path,
    feature: str,
    kind: Literal["spec", "plan"],
    model: str = "",
    max_chars: int | None = None,
) -> PreparedReview:
    """Prepare source-aware identical context for Python and native review transports."""
    root = project_root.resolve()
    feature_dir = root / ".specs" / "features" / feature
    feature_dir.resolve().relative_to(root / ".specs" / "features")
    paths = {
        feature_dir / "spec.md": "spec",
        root / ".specs/constitution.md": "constitution",
        root / ".specs/stacks/_default.md": "stack",
        root / ".specs/project.md": "project",
    }
    if kind == "plan":
        paths[feature_dir / "plan.md"] = "plan"
    sources, roles, owners, errors = _load_sources(root, paths, feature)
    settings = load_semantic_config(root / ".specs")
    if (
        not isinstance(cast(object, settings.review_max_chars), int)
        or settings.review_max_chars < 1000
    ):
        raise ValueError("review_max_chars_must_be_integer_at_least_1000")
    config = root / ".specs/semantic/config.yaml"
    dependencies = {
        "semantic_config": content_hash(
            config.read_bytes().decode("utf-8") if config.exists() else ""
        )
    }
    return prepare_review_context(
        feature,
        sources,
        kind=kind,
        model=current_review_model(root, model),
        source_roles=roles,
        source_features=owners,
        dependencies=dependencies,
        max_chars=max_chars if max_chars is not None else settings.review_max_chars,
        unresolved_references=tuple(sorted(set(errors))),
    )


def _load_sources(
    root: Path,
    paths: dict[Path, str],
    feature: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], list[str]]:
    """Load every canonical source and reachable local reference in the original order."""
    sources: dict[str, str] = {}
    roles: dict[str, str] = {}
    owners: dict[str, str] = {}
    errors: list[str] = []
    pending = list(paths)
    while pending:
        path = pending.pop(0)
        name = path.relative_to(root).as_posix()
        if name in sources:
            continue
        if len(sources) >= _MAX_SOURCES:
            errors.append("reference_inventory_over_budget")
            break
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"unread_source:{name}:{type(exc).__name__}")
            continue
        sources[name] = text
        roles[name] = paths.get(path, "reference")
        parts = path.parts
        owners[name] = parts[parts.index("features") + 1] if "features" in parts else feature
        references, missing = _references(path, text, root)
        errors.extend(missing)
        pending.extend(ref for ref in references if ref.relative_to(root).as_posix() not in sources)
    return sources, roles, owners, errors

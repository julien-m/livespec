"""Load canonical local review inputs without silently losing references (078 FR-002)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, TypedDict, cast
from urllib.parse import unquote, urlsplit

import mistune

from .config import load_semantic_config
from .review_context import PreparedReview, content_hash, prepare_review_context
from .review_feature_scope import resolve_existing_feature

# @spec FR-002: Sources — .specs/features/078-requirement-evidence-integrity/spec.md#fr-002
# @spec AC-002: Context — .specs/features/078-requirement-evidence-integrity/spec.md#ac-002
# Only an explicit adjacent descriptive verb/marker changes the default normative role.
_CONTEXT_PREFIX = re.compile(r"\b(?:inspect|informative|non-normative)\s*[:—-]?\s*$", re.I)
_MANDATORY_PREFIX = re.compile(r"\b(?:must|shall|required|read)\b", re.I)
_MAX_SOURCES = 128  # Preserve the existing fail-closed inventory bound.


class _MarkdownNode(TypedDict, total=False):
    """Relevant fields of the existing Mistune AST boundary."""

    type: str
    raw: str
    attrs: dict[str, object]
    children: list[_MarkdownNode]


def _link_role(prefix: str) -> str:
    """Keep mandatory wording authoritative over descriptive source inspection."""
    # Scope the marker to this sentence; an earlier sentence cannot demote a contract.
    sentence = re.split(r"[.!?\n]", prefix)[-1]
    if _CONTEXT_PREFIX.search(sentence) and not _MANDATORY_PREFIX.search(sentence):
        return "context"
    return "reference"


def _markdown_links(
    nodes: list[_MarkdownNode], prefix: str = ""
) -> tuple[list[tuple[str, str]], str]:
    """Extract genuine Markdown links while keeping inline prose classification local."""
    links: list[tuple[str, str]] = []
    for node in nodes:
        kind = node.get("type", "")
        if kind in {"block_code", "codespan", "block_html", "inline_html", "image"}:
            # Literal examples and HTML are retained in source bytes, never dependency edges.
            prefix += " "
            continue
        if kind == "link":
            target = node.get("attrs", {}).get("url")
            if isinstance(target, str):
                links.append((target, _link_role(prefix)))
        children = node.get("children", [])
        if children:
            # Formatting nodes preserve adjacent prose; each block gets its own prose context.
            inline = kind in {"link", "strong", "emphasis", "strikethrough"}
            nested, text = _markdown_links(children, prefix if inline else "")
            links.extend(nested)
            prefix = text if inline else ""
        else:
            prefix += node.get("raw", "")
    return links, prefix


def current_review_model(project_root: Path, model: str = "") -> str:
    """Resolve the configured model without inventing a provider identity.

    Args:
        project_root: Project containing optional semantic configuration.
        model: Explicit observed model identity, when supplied.

    Returns:
        Explicit or configured identity; empty if neither is resolved.

    Side effects:
        Reads semantic configuration only when the model is not explicit.
    """
    if model:
        return model
    config = load_semantic_config(project_root / ".specs")
    return config.review_model or next(iter(config.review_reviewers), "")


def review_receipt_path(project_root: Path, feature: str, kind: str) -> Path:
    """Return the actual existing owner's location for a disposable review receipt.

    Args:
        project_root: Project containing the feature inventory.
        feature: Existing canonical slug or unambiguous short slug.
        kind: Review purpose used for the receipt filename.

    Returns:
        Receipt path under the resolved existing feature directory.

    Raises:
        ValueError: The requested feature identity is unsafe or unresolved.
        OSError: The project inventory cannot be inspected.

    Side effects:
        Reads feature directory metadata; never creates the receipt.
    """
    if kind not in {"spec", "plan"}:
        raise ValueError("invalid_feature_review_kind")
    return resolve_existing_feature(project_root, feature) / ".reviews" / f"{kind}.json"


def _references(
    path: Path, text: str, project_root: Path
) -> tuple[list[tuple[Path, str]], list[str]]:
    paths: list[tuple[Path, str]] = []
    errors: list[str] = []
    ast = mistune.create_markdown(renderer="ast", plugins=["table"])(text)
    # Mistune's renderer union is untyped; renderer='ast' guarantees these token fields.
    links, _ = _markdown_links(cast(list[_MarkdownNode], ast))
    for raw_target, role in links:
        target = unquote(raw_target)
        parsed = urlsplit(target)
        if not parsed.path.endswith(".md"):
            continue
        if parsed.scheme or parsed.netloc:
            if role != "context":
                errors.append(f"external_contract_not_loaded:{target}")
            continue
        candidate = (path.parent / parsed.path).resolve()
        try:
            candidate.relative_to(project_root)
        except ValueError:
            errors.append(f"contract_outside_project:{target}")
            continue
        if candidate != path:
            # A fragment conservatively retains the entire target, including late obligations.
            paths.append((candidate, role))
    return paths, errors


def prepare_feature_review(
    project_root: Path,
    feature: str,
    kind: Literal["spec", "plan"],
    model: str = "",
    max_chars: int | None = None,
) -> PreparedReview:
    """Prepare the same canonical owner and sources for either review transport.

    Args:
        project_root: Project containing canonical review inputs.
        feature: Existing numbered slug or unambiguous short slug.
        kind: Spec or plan purpose required by the review obligation.
        model: Explicit observed identity; otherwise use configuration.
        max_chars: Explicit bounded budget; otherwise use configuration.

    Returns:
        Complete context or explicit unread-source and reference diagnostics.

    Raises:
        ValueError: Feature scope, configuration or budget is invalid.
        OSError: Project metadata or semantic configuration cannot be read.
    Side effects:
        Reads canonical source bytes and configuration; never calls a reviewer.
    """
    root = project_root.resolve()
    feature_dir = resolve_existing_feature(root, feature)
    feature = feature_dir.name
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
    pending = list(paths.items())
    while pending:
        path, discovered_role = pending.pop(0)
        name = path.relative_to(root).as_posix()
        role = paths.get(path, discovered_role)
        if name in sources:
            if roles[name] != "context" or role == "context":
                continue  # An already normative source is never demoted or traversed twice.
            text = sources[name]
        else:
            if len(sources) >= _MAX_SOURCES:
                errors.append("reference_inventory_over_budget")
                break
            try:
                path.resolve(strict=True).relative_to(root)
                text = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"unread_source:{name}:{type(exc).__name__}")
                continue  # Preserve the diagnostic; unread dependencies cannot certify readiness.
            sources[name] = text
            parts = path.relative_to(root).parts
            owners[name] = parts[2] if parts[:2] == (".specs", "features") else feature
        roles[name] = role
        if role == "context":
            # Inspect the full source without adopting its internal documentation contract.
            continue
        references, missing = _references(path, text, root)
        errors.extend(missing)
        pending.extend(references)
    return sources, roles, owners, errors

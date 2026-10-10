"""Scoped documentary acceptance using the existing grounded review transport."""

# @spec(FR-009)
# @spec(FR-016)

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from validator.acceptance_requirements import acceptance_inventory
from validator.execution_scope import _excluded, _referenced_inputs
from validator.normative_identity import normative_hash

from .review_context import PreparedReview, prepare_review_context
from .review_contract import ReviewReceipt, validate_review_result
from .review_files import prepare_feature_review, review_receipt_path
from .review_receipts import load_review_receipt, save_review_receipt, verify_review_receipt


class AcceptanceReviewInputs(BaseModel):
    """Generated source inventory; additional provenance remains visible in its raw JSON."""

    model_config = ConfigDict(extra="allow", strict=True)
    source_paths: list[str]
    current_hashes: dict[str, str | None]
    feature_spec_paths: list[str]
    identity_policy: Literal["normative-identity-v2"]


def prepare_acceptance_review(
    root: Path, feature: str, model: str = "", max_chars: int | None = None
) -> PreparedReview:
    """Bind actual documentary inputs and current scope independently of ordinary plan review."""
    base = prepare_feature_review(root, feature, "plan", model, max_chars)
    sources: dict[str, str] = {}
    roles: dict[str, str] = {}
    for section in base.sections:
        sources[section.source] = sources.get(section.source, "") + section.text
        roles[section.source] = section.role
    obligations = tuple(
        item
        for item in acceptance_inventory(
            root, feature, spec_text=sources[f".specs/features/{feature}/spec.md"]
        )
        if item.evidence_kind == "review"
    )
    if not obligations:
        raise ValueError("documentary_acceptance_scope_empty")
    paths = {path for item in obligations for path in item.review_inputs}
    for path in sorted(paths):
        for name, content in _manifest_sources(root, feature, path).items():
            sources[name], roles[name] = content, "plan"
    return prepare_review_context(
        feature,
        sources,
        kind="plan",
        model=base.reviewer_model,
        source_roles=roles,
        source_features=_source_owners(sources, feature),
        dependencies={
            **base.dependencies,
            "review_purpose": "acceptance",
            "acceptance_evidence_policy": "2",
        },
        max_chars=base.max_chars,
        unresolved_references=base.errors,
        requirement_scope=tuple(item.requirement_id for item in obligations),
    )


def ingest_acceptance_review(
    root: Path,
    feature: str,
    raw_results: list[str],
    synthesis: str | None = None,
    *,
    model: str = "",
    max_chars: int | None = None,
) -> tuple[ReviewReceipt, Path]:
    """Ingest actual reviewer output; no caller-written acceptance boolean is accepted."""
    prepared = prepare_acceptance_review(root, feature, model, max_chars)
    receipt = validate_review_result(prepared, raw_results, synthesis)
    path = save_review_receipt(review_receipt_path(root, feature, "acceptance"), receipt)
    return receipt, path


def verify_acceptance_review(
    root: Path, feature: str, path: Path, *, model: str = "", max_chars: int | None = None
) -> bool:
    """Reconstruct purpose, declaration, source and policy freshness at every boundary."""
    receipt = load_review_receipt(path)
    prepared = prepare_acceptance_review(root, feature, model, max_chars)
    return receipt.ready and verify_review_receipt(receipt, prepared)


def _manifest_sources(root: Path, feature: str, name: str) -> dict[str, str]:
    manifest_path = _contained(root, name)
    raw = manifest_path.read_bytes().decode("utf-8")
    manifest = AcceptanceReviewInputs.model_validate_json(raw)
    _verify_current_inputs(root, feature, manifest)
    if not manifest.source_paths:
        raise ValueError("acceptance_review_sources_empty")
    return {
        name: raw,
        **{
            path: _contained(root, path).read_bytes().decode("utf-8")
            for path in manifest.source_paths
        },
    }


def _contained(root: Path, name: str) -> Path:
    path = root / name
    if Path(name).is_absolute():
        raise ValueError("acceptance_input_must_be_project_relative")
    path.resolve().relative_to(root.resolve())
    return path


def _verify_current_inputs(root: Path, feature: str, manifest: AcceptanceReviewInputs) -> None:
    actual_specs = sorted(
        path.relative_to(root).as_posix() for path in (root / ".specs/features").glob("*/spec.md")
    )
    if actual_specs != manifest.feature_spec_paths or not set(actual_specs).issubset(
        manifest.current_hashes
    ):
        raise ValueError("acceptance_feature_inventory_stale_or_incomplete")
    required = set(manifest.source_paths) | set(_referenced_inputs(root, feature))
    for name, expected in manifest.current_hashes.items():
        path = root / name
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("acceptance_input_must_be_project_relative")
        if name not in required and _generated_input(path, root, feature):
            continue
        if path.is_symlink():
            actual = hashlib.sha256(path.readlink().as_posix().encode()).hexdigest()
        elif path.is_file():
            path.resolve().relative_to(root.resolve())
            data = path.read_bytes()
            lifecycle = name in {
                f".specs/features/{feature}/spec.md",
                f".specs/features/{feature}/plan.md",
            }
            actual = (
                normative_hash(data.decode("utf-8"), lifecycle_document=True)
                if lifecycle
                else hashlib.sha256(data).hexdigest()
            )
        elif path.exists():
            raise ValueError("acceptance_input_not_regular_file")
        else:
            actual = None
        if actual != expected:
            raise ValueError(f"acceptance_input_stale:{name}")


def _generated_input(path: Path, root: Path, feature: str) -> bool:
    """Reuse exact execution exclusions; explicit documentary inputs override them."""
    return any(
        _excluded(parent, root, feature)
        for parent in (path, *path.parents)
        if parent != root and root in parent.parents
    )


def _source_owners(sources: dict[str, str], feature: str) -> dict[str, str]:
    """Preserve qualification of every referenced feature from the common loader."""
    result = {}
    for name in sources:
        parts = Path(name).parts
        result[name] = parts[parts.index("features") + 1] if "features" in parts else feature
    return result

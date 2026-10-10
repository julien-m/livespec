"""Existing owner identity is stable across review and new-goal boundaries (078 FR-004)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from validator.goal_contracts import compile_command_goal
from validator.semantic import review_context
from validator.semantic.review_api import ingest_feature_review, verify_feature_review
from validator.semantic.review_context import PreparedReview
from validator.semantic.review_feature_scope import resolve_existing_feature
from validator.semantic.review_files import prepare_feature_review, review_receipt_path

ROOT = Path(__file__).parents[1]
FEATURE = "001-retention"


def _project(root: Path, feature: str = FEATURE) -> Path:
    """Build isolated canonical sources at the actual review filesystem boundary."""
    files = {
        f"features/{feature}/spec.md": (
            "# Retention\n## FR-001\nDelete exports after 24 hours.\n"
            "## AC-001\nExports older than 24 hours are absent.\n"
        ),
        f"features/{feature}/plan.md": "Delete exports when their age reaches 24 hours.\n",
        "constitution.md": "Keep the contract authoritative.\n",
        "stacks/_default.md": "Python\n",
        "project.md": "Export management\n",
    }
    for name, text in files.items():
        path = root / ".specs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root / ".specs/features" / feature


def _raw(prepared: PreparedReview) -> str:
    """Supply only a fake reviewer transport response, never a production resolver."""
    batch = prepared.batches[0]
    sections = {section.section_id: section for section in prepared.sections}
    plans = [sections[key] for key in batch.section_ids if sections[key].role == "plan"]
    conclusions = [
        {
            "requirement_id": requirement.requirement_id,
            "disposition": "covered",
            "rationale": "The reviewed retention obligation is preserved in these exact bytes.",
            "source_citations": [
                {"section_id": key, "excerpt": sections[key].text}
                for key in requirement.section_ids
            ],
            "plan_citations": [
                {"section_id": section.section_id, "excerpt": section.text} for section in plans
            ],
        }
        for requirement in prepared.requirements
    ]
    return json.dumps(
        {
            "batch_id": batch.batch_id,
            "reviewed_section_ids": list(batch.section_ids),
            "conclusions": conclusions,
            "ambiguities": [],
            "extra_scope": [],
            "findings": [],
            "confidence": 5,
        }
    )


# @spec AC-002: Complete canonical context
#   — .specs/features/078-requirement-evidence-integrity/spec.md#ac-002
@pytest.mark.parametrize("kind", ["spec", "plan"])
def test_short_scope_preserves_exact_context_and_canonical_receipt(
    tmp_path: Path, kind: Literal["spec", "plan"]
) -> None:
    """Short and numbered requests consume identical complete sources and actual owners."""
    feature = _project(tmp_path)
    canonical = prepare_feature_review(tmp_path, FEATURE, kind, "reviewer/actual")
    short = prepare_feature_review(tmp_path, "retention", kind, "reviewer/actual")
    assert canonical.complete and short.complete
    assert short == canonical
    assert short.feature == feature.name
    assert {item.requirement_id for item in short.requirements} == {
        f"{FEATURE}:FR-001",
        f"{FEATURE}:AC-001",
    }
    receipt, path = ingest_feature_review(
        tmp_path, "retention", kind, [_raw(short)], model="reviewer/actual"
    )
    assert receipt.ready and receipt.complete
    assert path == feature / ".reviews" / f"{kind}.json"
    assert review_receipt_path(tmp_path, FEATURE, kind) == path
    assert verify_feature_review(
        tmp_path, "retention", path, model="reviewer/actual", expected_kind=kind
    )
    assert verify_feature_review(
        tmp_path, FEATURE, path, model="reviewer/actual", expected_kind=kind
    )


# @spec AC-004: Exact current identity
#   — .specs/features/078-requirement-evidence-integrity/spec.md#ac-004
@pytest.mark.parametrize("kind", ["spec", "plan"])
@pytest.mark.parametrize("change", ["source", "model", "kind", "config"])
def test_short_scope_does_not_reuse_stale_or_foreign_evidence(
    tmp_path: Path, kind: Literal["spec", "plan"], change: str
) -> None:
    """Canonical resolution cannot bypass current source, model, purpose or dependency checks."""
    feature = _project(tmp_path)
    prepared = prepare_feature_review(tmp_path, FEATURE, kind, "reviewer/actual")
    receipt, path = ingest_feature_review(
        tmp_path, FEATURE, kind, [_raw(prepared)], model="reviewer/actual"
    )
    assert receipt.ready
    model = "reviewer/actual"
    expected: Literal["spec", "plan"] = kind
    if change == "source":
        (feature / "spec.md").write_text("## FR-001\nRetain exports forever.\n")
    elif change == "model":
        model = "reviewer/other"
    elif change == "kind":
        expected = "plan" if kind == "spec" else "spec"
    else:
        config = tmp_path / ".specs/semantic/config.yaml"
        config.parent.mkdir()
        config.write_text("review_max_chars: 100000\n")
    assert not verify_feature_review(
        tmp_path, "retention", path, model=model, expected_kind=expected
    )


@pytest.mark.parametrize("version", ["POLICY_VERSION", "SCHEMA_VERSION", "PROMPT_VERSION"])
def test_short_scope_rejects_receipts_from_a_prior_review_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    """Protocol releases invalidate an otherwise unchanged canonical receipt through aliases."""
    _project(tmp_path)
    prepared = prepare_feature_review(tmp_path, FEATURE, "spec", "reviewer/actual")
    receipt, path = ingest_feature_review(
        tmp_path, FEATURE, "spec", [_raw(prepared)], model="reviewer/actual"
    )
    assert receipt.ready
    assert verify_feature_review(
        tmp_path, "retention", path, model="reviewer/actual", expected_kind="spec"
    )
    monkeypatch.setattr(review_context, version, "future-protocol-version")
    assert not verify_feature_review(
        tmp_path, "retention", path, model="reviewer/actual", expected_kind="spec"
    )


@pytest.mark.parametrize("slug", ["001.1-retention", "retention"])
def test_explicit_dotted_and_legacy_directory_identities_are_preserved(
    tmp_path: Path, slug: str
) -> None:
    """Existing historical forms keep their own identity rather than acquiring a new number."""
    feature = _project(tmp_path, slug)
    assert resolve_existing_feature(tmp_path, "retention") == feature
    assert resolve_existing_feature(tmp_path, slug) == feature


@pytest.mark.parametrize("other", ["002-retention", "retention"])
def test_colliding_short_names_are_ambiguous_even_with_an_exact_legacy_folder(
    tmp_path: Path, other: str
) -> None:
    """All actual matches count; an exact short directory cannot hide another canonical owner."""
    feature = _project(tmp_path)
    _project(tmp_path, other)
    with pytest.raises(ValueError, match="existing_feature_ambiguous"):
        resolve_existing_feature(tmp_path, "retention")
    assert resolve_existing_feature(tmp_path, FEATURE) == feature


@pytest.mark.parametrize(
    "slug",
    ["missing", "002-missing", "../retention", "a/b", "a\\b", "", "Retention", "NNN-feature-name"],
)
def test_absent_or_invalid_scope_never_allocates_a_feature(tmp_path: Path, slug: str) -> None:
    """Resolution fails before mutation for missing owners and unsafe path-like input."""
    _project(tmp_path)
    before = sorted(path.name for path in (tmp_path / ".specs/features").iterdir())
    with pytest.raises(ValueError):
        resolve_existing_feature(tmp_path, slug)
    assert sorted(path.name for path in (tmp_path / ".specs/features").iterdir()) == before


@pytest.mark.parametrize("external", [False, True])
def test_feature_symlink_cannot_claim_a_canonical_owner(tmp_path: Path, external: bool) -> None:
    """Linked aliases reject whether their target is inside or outside the feature inventory."""
    root = tmp_path / "project"
    target = _project(root, "002-target") if not external else tmp_path / "outside"
    if external:
        _project(root)
        target.mkdir()
    alias = root / ".specs/features/003-retention"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="linked_feature_not_allowed"):
        resolve_existing_feature(root, alias.name)


def test_inventory_and_canonical_source_escapes_fail_before_bytes_are_loaded(
    tmp_path: Path,
) -> None:
    """Escaping inventory and canonical source links cannot become complete review context."""
    root = tmp_path / "project"
    feature = _project(root)
    outside = tmp_path / "outside.md"
    outside.write_text("FR-999: External bytes must not enter canonical context.\n")
    (feature / "spec.md").unlink()
    (feature / "spec.md").symlink_to(outside)
    prepared = prepare_feature_review(root, "retention", "spec", "reviewer/actual")
    assert not prepared.complete
    assert all("External bytes" not in section.text for section in prepared.sections)
    inventory = root / ".specs/features"
    inventory.rename(tmp_path / "outside-features")
    inventory.symlink_to(tmp_path / "outside-features", target_is_directory=True)
    with pytest.raises(ValueError, match="feature_inventory_missing_or_unconfined"):
        resolve_existing_feature(root, "retention")


def test_owner_is_relative_to_project_even_when_an_ancestor_is_named_features(
    tmp_path: Path,
) -> None:
    """Qualified requirements derive from the selected feature rather than ancestor path names."""
    root = tmp_path / "features/workspace"
    _project(root)
    prepared = prepare_feature_review(root, "retention", "spec", "reviewer/actual")
    assert {item.requirement_id for item in prepared.requirements} == {
        f"{FEATURE}:FR-001",
        f"{FEATURE}:AC-001",
    }


@pytest.mark.parametrize("command", ["spec-check", "spec-fix"])
def test_new_existing_feature_goals_freeze_same_canonical_identity(
    tmp_path: Path, command: str
) -> None:
    """A new short request compiles the same immutable hash and bindings as its actual owner."""
    _project(tmp_path)
    flags = "--model=reviewer/actual --review-max-chars=200000"
    numbered = compile_command_goal(
        command, project_root=tmp_path, livespec_root=ROOT, feature=FEATURE, flags=flags
    )
    short = compile_command_goal(
        command, project_root=tmp_path, livespec_root=ROOT, feature="retention", flags=flags
    )
    assert short.goal_hash == numbered.goal_hash
    assert short.canonical_json == numbered.canonical_json
    assert short.payload["feature"] == FEATURE


def test_bootstrap_and_collection_do_not_require_an_existing_feature(tmp_path: Path) -> None:
    """Root bootstrap and collection goals retain their absence of a selected existing owner."""
    initial = compile_command_goal("spec-init", project_root=tmp_path, livespec_root=ROOT)
    assert initial.payload["feature"] is None
    _project(tmp_path)
    collection = compile_command_goal(
        "spec-fix", project_root=tmp_path, livespec_root=ROOT, flags="--all"
    )
    assert collection.payload["feature"] is None

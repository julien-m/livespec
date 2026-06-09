# LiveSpec traceability anchors
# @spec(AC-013)
# @spec(AC-014)
# @spec(AC-015)
# @spec(AC-016)
# @spec(AC-017)

"""Tests for v2 journey auto-assignment and bootstrap services."""

from __future__ import annotations

from pathlib import Path

from validator.journeys.assignment import infer_journey_assignment
from validator.journeys.bootstrap import bootstrap_journey_candidates


def _write_spec(specs: Path, slug: str, body: str) -> None:
    feature_dir = specs / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        f"---\nstatus: Implemented\n---\n# {slug}\n\n{body}",
        encoding="utf-8",
    )


def test_assignment_infers_features_and_refs_from_free_form_intent(tmp_path: Path) -> None:
    """FR-013: free-form journey creation proposes qualified refs with evidence."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_spec(
        specs,
        "001-onboarding",
        "## Acceptance Criteria\n- **AC-001:** User signs up.\n",
    )
    _write_spec(
        specs,
        "012-projects",
        "## Functional Requirements\n- **FR-003:** User creates a first project.\n",
    )

    candidate = infer_journey_assignment(
        tmp_path,
        "first user signs up and creates a first project",
    )

    assert candidate.journey_id == "first-user-signs-up-and-creates-a-first-project"
    assert {ref.feature for ref in candidate.covers} == {"001-onboarding", "012-projects"}
    assert {ref.ref for ref in candidate.covers} == {"AC-001", "FR-003"}
    assert all(item.source_path.endswith("spec.md") for item in candidate.evidence)


def test_bootstrap_proposes_candidates_without_writing_journey_files(tmp_path: Path) -> None:
    """FR-015: bootstrap scans old features and returns candidates without writes."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_spec(
        specs,
        "001-onboarding",
        "## User Scenarios & Testing\n"
        "User signs up and creates a first project.\n\n"
        "## Acceptance Criteria\n- **AC-001:** User signs up.\n",
    )
    _write_spec(
        specs,
        "012-projects",
        "## Functional Requirements\n- **FR-003:** User creates a first project.\n",
    )

    candidates = bootstrap_journey_candidates(tmp_path)

    assert candidates
    assert not (specs / "journeys").exists()
    assert candidates[0].confidence > 0
    assert candidates[0].ambiguous is False

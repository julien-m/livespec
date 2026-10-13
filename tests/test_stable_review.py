"""Spec and plan reviews stay current until their requirements change (feature 089)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from tests.stable_review_support import FEATURE, SPEC, edit_spec, make_root, review_both
from validator.progression_gate import require_progression
from validator.semantic.review_api import verify_feature_review
from validator.semantic.review_files import prepare_feature_review, review_receipt_path
from validator.semantic.review_receipts import load_review_receipt, verify_review_receipt
from validator.semantic.review_stability import requirement_projection, reviewed_against


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_root(tmp_path)


def _current(root: Path) -> tuple[bool, bool]:
    def check(kind: Literal["spec", "plan"]) -> bool:
        path = review_receipt_path(root, FEATURE, kind)
        return verify_feature_review(root, FEATURE, path, expected_kind=kind)

    return check("spec"), check("plan")


# @spec AC-002: Only requirement changes make a review stale
#   — .specs/features/089-stable-review-identity/spec.md#ac-002
@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("- **Clock skew:** use the server clock.", "- **Clock skew:** use NTP time.\n\nMore."),
        ("Medium criticality; Local", "Low criticality; Local"),
        ("- **In scope:** exports.", "- **In scope:** exports\n  and archives."),
        ("Delete exports after 24 hours.", "Delete   exports after **24 hours**."),
        ("status: Approved", "status: Implemented"),
    ],
    ids=["edge-case", "qe", "scope", "formatting", "lifecycle"],
)
def test_non_requirement_edits_keep_both_reviews(root: Path, old: str, new: str) -> None:
    edit_spec(root, old, new)
    assert _current(root) == (True, True)
    require_progression(root, FEATURE, "implement", model="reviewer/v1")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Exports older than 24 hours are absent.", "Exports older than 48 hours are absent."),
        ("Delete exports after 24 hours.", "Delete exports after 48 hours."),
        ("Then it is deleted", "Then it is archived"),
    ],
    ids=["acceptance", "functional", "gherkin"],
)
def test_requirement_edits_make_both_reviews_stale(root: Path, old: str, new: str) -> None:
    edit_spec(root, old, new)
    assert _current(root) == (False, False)


def test_plan_edit_makes_only_the_plan_review_stale(root: Path) -> None:
    plan = root / ".specs/features" / FEATURE / "plan.md"
    plan.write_text(plan.read_text().replace("hourly", "daily"))
    assert _current(root) == (True, False)


# @spec AC-001: The budget is not part of the review identity
#   — .specs/features/089-stable-review-identity/spec.md#ac-001
def test_review_prepared_with_another_budget_stays_current(root: Path) -> None:
    review_both(root, max_chars=120000)
    assert _current(root) == (True, True)
    receipt = load_review_receipt(review_receipt_path(root, FEATURE, "spec"))
    prepared = prepare_feature_review(root, FEATURE, "spec", "reviewer/v1")
    assert receipt.context_hash != prepared.context_hash
    assert reviewed_against(receipt, prepared) == receipt.reviewed


# @spec AC-003: Strict comparison without or against a tampered context
#   — .specs/features/089-stable-review-identity/spec.md#ac-003
def test_strict_paths_and_tampered_context(root: Path) -> None:
    edit_spec(root, "use the server clock", "use NTP time")
    path = review_receipt_path(root, FEATURE, "spec")
    prepared = prepare_feature_review(root, FEATURE, "spec", "reviewer/v1")
    receipt = load_review_receipt(path)
    assert not verify_review_receipt(receipt, prepared)  # Acceptance and mapping use this.
    data = json.loads(path.read_text())
    data["reviewed"]["sections"][-1]["text"] = "Tampered text."
    path.write_text(json.dumps(data))
    assert _current(root)[0] is False
    del data["reviewed"]
    path.write_text(json.dumps(data))
    assert _current(root)[0] is False


def test_projection_keeps_requirements_and_gherkin_only() -> None:
    projection = requirement_projection(SPEC)
    assert "Exports older than 24 hours are absent." in projection
    assert "- FR-001: Delete exports after 24 hours. Maps to: AC-001." in projection
    assert "Then it is deleted" in projection
    assert "Clock skew" not in projection and "criticality" not in projection
    assert requirement_projection("## FR-002\nKeep it.\n## Notes\nFree.\n") == "## FR-002\nKeep it."


def test_consistent_edit_of_the_stored_context_stays_stale(root: Path) -> None:
    old, new = "older than 24 hours are absent", "older than 48 hours are absent"
    edit_spec(root, old, new)
    assert _current(root) == (False, False)
    for kind in ("spec", "plan"):
        path = review_receipt_path(root, FEATURE, kind)
        path.write_text(path.read_text().replace(old, new))
    assert _current(root) == (False, False)


def test_review_with_a_larger_budget_stays_current_under_the_default(root: Path) -> None:
    edit_spec(root, "- **Clock skew:** use the server clock.", "- " + "Long note. " * 7000)
    review_both(root, max_chars=120000)
    edit_spec(root, "Long note. Long", "Long remark. Long")
    assert _current(root) == (True, True)


def test_new_success_criterion_makes_the_review_stale(root: Path) -> None:
    edit_spec(
        root,
        "## Edge Cases",
        "## Success Criteria\n\n- **SC-001:** Disk stays small.\n\n## Edge Cases",
    )
    assert _current(root) == (False, False)


@pytest.mark.parametrize(
    "heading",
    ["## 5. Acceptance Criteria", "## Acceptance Criteria (v2)", "## Critères d'acceptation"],
)
def test_projection_reads_decorated_requirement_headings(heading: str) -> None:
    text = f"{heading}\n\n| AC-002 | Exports are listed. |\n\n## Notes\n\nFree.\n"
    assert requirement_projection(text).endswith("| AC-002 | Exports are listed. |")
    assert "AC-003: Kept anywhere." in requirement_projection("## Notes\nAC-003: Kept anywhere.\n")


def test_empty_source_keeps_the_stable_path(root: Path) -> None:
    (root / ".specs/project.md").write_text("")
    review_both(root)
    edit_spec(root, "use the server clock", "use NTP time")
    assert _current(root) == (True, True)

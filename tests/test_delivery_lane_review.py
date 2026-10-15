"""The spec review in the lane: reviewed QE and contestable criticality (feature 086 AC-009)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from tests.delivery_support import FEATURE, MODEL, DeliveryProject, make_project, spec_text

HIGH = "- **Risk:** High criticality; Shared blast radius; primary risk Functional."


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DeliveryProject:
    project = make_project(tmp_path, spec_text(HIGH))
    monkeypatch.chdir(project.root)
    return project


def _lane(project: DeliveryProject) -> tuple[str, list[str], object]:
    _, payload = project.json("delivery", "lane", "--feature", FEATURE, "--model", MODEL)
    codes = [r["code"] for r in cast(list[dict[str, Any]], payload["reasons"])]
    return str(payload["lane"]), codes, payload["criticality_contested"]


# @spec AC-009: Contestable criticality and reviewed QE
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-009
def test_reviewer_lowers_an_author_high_to_medium(project: DeliveryProject) -> None:
    project.review_spec()
    assert _lane(project)[:2] == ("full", ["criticality_high"])
    project.review_spec(criticality="Medium")
    lane, codes, contested = _lane(project)
    assert (lane, codes) == ("light", [])
    assert contested == {
        "author": "high",
        "reviewer": "medium",
        "justification": "Local arithmetic with no persisted data.",
    }


def test_reviewer_raises_medium_to_high(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = make_project(tmp_path)
    monkeypatch.chdir(project.root)
    project.review_spec(criticality="High")
    lane, codes, contested = _lane(project)
    assert (lane, codes, contested) == ("full", ["criticality_high"], None)


def test_contest_never_lowers_a_wide_blast_radius(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wide = "- **Risk:** High criticality; External blast radius; primary risk Security."
    project = make_project(tmp_path, spec_text(wide))
    monkeypatch.chdir(project.root)
    project.review_spec(criticality="Low")
    assert _lane(project)[:2] == ("full", ["blast_radius_wide"])


def test_qe_edit_after_review_keeps_the_reviewed_classification(project: DeliveryProject) -> None:
    project.review_spec()
    spec = project.feature_dir / "spec.md"
    spec.write_text(spec.read_text().replace("High criticality", "Low criticality"))
    lane, codes, _ = _lane(project)
    assert (lane, codes) == ("full", ["criticality_high"])  # The reviewed QE says High.


def test_high_added_after_the_review_is_not_contested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = make_project(tmp_path)
    monkeypatch.chdir(project.root)
    project.review_spec(criticality="Medium")
    spec = project.feature_dir / "spec.md"
    spec.write_text(spec.read_text().replace("Medium criticality", "High criticality"))
    lane, codes, contested = _lane(project)
    assert (lane, codes, contested) == ("full", ["criticality_high"], None)


def test_contest_needs_a_current_review(project: DeliveryProject) -> None:
    project.review_spec(criticality="Medium")
    spec = project.feature_dir / "spec.md"
    spec.write_text(spec.read_text().replace("their sum", "their product"))
    lane, codes, contested = _lane(project)
    assert (lane, contested) == ("full", None)
    assert codes == ["criticality_high", "spec_review_not_current"]

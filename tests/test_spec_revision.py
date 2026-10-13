"""A spec revised during implementation and reviewed once at the end (feature 089)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.stable_review_support import FEATURE, edit_spec, make_root, review_both
from validator.cli import app
from validator.delivery.review import verify_review
from validator.progression_gate import ProgressionBlocked, require_progression

AC_EDIT = ("Exports older than 24 hours are absent.", "Exports older than 48 hours are absent.")


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_root(tmp_path)
    monkeypatch.chdir(root)
    return root


def _revision(action: str) -> tuple[int, dict[str, object]]:
    args = ["delivery", "revision", action, "--feature", FEATURE, "--json"]
    result = CliRunner().invoke(app, args, catch_exceptions=False)
    return result.exit_code, json.loads(result.output)


# @spec AC-004: Opening a spec revision
#   — .specs/features/089-stable-review-identity/spec.md#ac-004
def test_open_records_both_reviews_once(root: Path) -> None:
    assert _revision("status") == (0, {"feature": FEATURE, "open": False, "error": ""})
    code, payload = _revision("open")
    assert (code, payload["open"], payload["error"]) == (0, True, "")
    assert isinstance(payload["spec"], str) and isinstance(payload["plan"], str)
    status = _revision("status")[1]
    assert (status["open"], status["spec"]) == (True, payload["spec"])
    again = {"feature": FEATURE, "open": True, "error": "spec_revision_open"}
    assert _revision("open") == (1, again)


def test_open_needs_current_reviews(root: Path) -> None:
    edit_spec(root, *AC_EDIT)
    code, payload = _revision("open")
    assert (code, payload["open"], payload["error"]) == (1, False, "spec_review_not_current")
    assert _revision("status")[1]["open"] is False


# @spec AC-005: Progressions while the revision is open
#   — .specs/features/089-stable-review-identity/spec.md#ac-005
def test_open_revision_lets_implementation_go_on_but_not_completion(root: Path) -> None:
    _revision("open")
    edit_spec(root, *AC_EDIT)
    require_progression(root, FEATURE, "implement", model="reviewer/v1")
    require_progression(root, FEATURE, "test", model="reviewer/v1")
    with pytest.raises(ProgressionBlocked, match="spec_revision_open"):
        require_progression(root, FEATURE, "complete", model="reviewer/v1")
    outcome = verify_review(root, FEATURE, "full")
    assert outcome.verdict == "BLOCKED"
    assert [reason.code for reason in outcome.reasons] == ["spec_revision_open"]


def test_without_revision_a_requirement_edit_blocks_implementation(root: Path) -> None:
    edit_spec(root, *AC_EDIT)
    with pytest.raises(ProgressionBlocked):
        require_progression(root, FEATURE, "implement", model="reviewer/v1")


# @spec AC-006: Closing after one review of the revised spec
#   — .specs/features/089-stable-review-identity/spec.md#ac-006
def test_close_needs_one_new_review_of_the_revised_sources(root: Path) -> None:
    assert _revision("close")[1]["error"] == "no_spec_revision"
    _revision("open")
    edit_spec(root, *AC_EDIT)
    edit_spec(root, "Delete exports after 24 hours.", "Delete exports after 48 hours.")
    code, payload = _revision("close")
    assert (code, payload["open"], payload["error"]) == (1, True, "spec_review_not_current")
    review_both(root)
    assert _revision("close") == (0, {"feature": FEATURE, "open": False, "error": ""})
    require_progression(root, FEATURE, "complete", model="reviewer/v1")

"""A finalize status change keeps semantic reviews current; normative edits do not (078 FR-004).

Regression for the Handy report: after a READY plan, ``livespec finalize apply --status``
rewrote the frontmatter ``status:``/``updated:`` and the header ``- **Status:**`` line, and
``livespec validate <feature> --progression implement`` answered
``clarify_not_ready:stale_or_incomplete_spec_review``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import review_existing_project
from tests.test_finalize import _make_specs_tree
from validator.cli import app
from validator.progression_gate import ProgressionBlocked, require_progression

FEATURE = "004-notifications"

# Handy-shaped spec: extra frontmatter keys and an explicit `## Header` band.
_SPEC = """\
---
feature: notifications
title: Notifications
priority: P1
status: {status}
created: 2026-10-12
updated: 2026-10-12
---

# Feature Spec: Notifications

## Header

- **Feature:** Notifications
- **Branch:** None — specification only
- **Date:** 2026-10-12
- **Status:** {status}
- **Feature Number:** 004

## Requirements

- **FR-001:** Deliver a push notification within 5 seconds.

## Acceptance Criteria

- **AC-001:** Given a new message, when it arrives, then a notification shows within 5 seconds.
"""


def _reviewed(tmp_path: Path, status: str) -> Path:
    _make_specs_tree(tmp_path)
    spec = tmp_path / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(_SPEC.format(status=status))
    review_existing_project(tmp_path, FEATURE)
    require_progression(tmp_path, FEATURE, "implement")
    return spec


def _finalize(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    monkeypatch.chdir(tmp_path)
    entry = tmp_path / "entry.md"
    entry.write_text("Plan: technical plan generated\n")
    command = ["finalize", "apply", "--feature", FEATURE, "--command", "spec-plan"]
    options = ["--status", status, "--entry-file", str(entry), "--json"]
    result = CliRunner().invoke(app, [*command, *options])
    assert result.exit_code == 0, result.output


# @spec FR-004: Lifecycle metadata never invalidates semantic review identity
#   — .specs/features/078-requirement-evidence-integrity/spec.md#fr-004
@pytest.mark.parametrize(
    ("before", "after"),
    [("Draft", "Planned"), ("Review", "Planned"), ("Planned", "In Progress")],
)
def test_finalize_status_change_keeps_reviews_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, before: str, after: str
) -> None:
    spec = _reviewed(tmp_path, before)
    _finalize(tmp_path, monkeypatch, after)
    text = spec.read_text()
    assert f"status: {after}\n" in text and f"- **Status:** {after}\n" in text
    require_progression(tmp_path, FEATURE, "implement")


def test_acceptance_change_after_finalize_makes_review_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = _reviewed(tmp_path, "Draft")
    _finalize(tmp_path, monkeypatch, "Planned")
    spec.write_text(spec.read_text().replace("within 5 seconds.\n", "within 50 seconds.\n"))
    with pytest.raises(ProgressionBlocked, match="stale_or_incomplete_spec_review"):
        require_progression(tmp_path, FEATURE, "implement")


def test_reviewer_model_mismatch_is_named(tmp_path: Path) -> None:
    _reviewed(tmp_path, "Planned")
    with pytest.raises(ProgressionBlocked, match="spec_review_model_mismatch:reviewer/v1!=other"):
        require_progression(tmp_path, FEATURE, "implement", model="other")

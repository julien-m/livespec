"""One independent review of the complete feature diff (feature 086 AC-003 to AC-006)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from tests.delivery_support import FEATURE, MODEL, DeliveryProject, git, make_project, report


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DeliveryProject:
    """A light-lane project with one changed source file and one new test."""
    project = make_project(tmp_path)
    project.review_spec()
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "reviewed spec")
    project.write("calc.py", "def add(a, b):\n    return b + a\n")
    project.write(
        "tests/test_calc.py",
        "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    )
    project.write(f".specs/features/{FEATURE}/implementation.md", "# Implementation\n")
    monkeypatch.chdir(project.root)
    return project


SCOPE = ["calc.py", "tests/test_calc.py"]


def _prepare(project: DeliveryProject) -> tuple[int, dict[str, object]]:
    return project.json(
        "delivery", "review", "prepare", "--feature", FEATURE, "--base", "HEAD~1", "--model", MODEL
    )


def _record(
    project: DeliveryProject, kind: str, payload: dict[str, object]
) -> tuple[int, dict[str, object]]:
    path = project.root.parent / f"report-{kind}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return project.json(
        "delivery", "review", "record", "--feature", FEATURE, "--kind", kind, "--report", str(path)
    )


def _verify(project: DeliveryProject) -> tuple[int, list[str]]:
    code, payload = project.json(
        "delivery", "review", "verify", "--feature", FEATURE, "--model", MODEL
    )
    return code, [r["code"] for r in cast(list[dict[str, Any]], payload["reasons"])]


def _codes(payload: dict[str, object]) -> list[str]:
    return [r["code"] for r in cast(list[dict[str, Any]], payload["reasons"])]


# @spec AC-003: Scope of the complete diff
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-003
def test_prepare_hashes_every_counted_path(project: DeliveryProject) -> None:
    code, scope = _prepare(project)
    assert code == 0 and scope["error"] == ""
    assert sorted(cast(dict[str, str], scope["files"])) == SCOPE
    assert scope["lane"] == "light" and len(str(scope["base_commit"])) == 40
    assert (project.feature_dir / ".reviews" / "delivery-scope.json").is_file()


def test_prepare_reports_empty_scope_and_unknown_base(
    project: DeliveryProject, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, scope = project.json(
        "delivery", "review", "prepare", "--feature", FEATURE, "--base", "no-such-rev"
    )
    assert (code, scope["error"]) == (1, "diff_unavailable")
    clean = make_project(tmp_path / "clean")
    monkeypatch.chdir(clean.root)
    code, scope = clean.json(
        "delivery", "review", "prepare", "--feature", FEATURE, "--base", "HEAD"
    )
    assert (code, scope["error"]) == (1, "empty_scope")


def test_base_newer_than_the_feature_start_is_refused(project: DeliveryProject) -> None:
    code, scope = project.json(
        "delivery", "review", "prepare", "--feature", FEATURE, "--base", "HEAD", "--model", MODEL
    )
    assert (code, scope["error"]) == (1, "base_not_feature_start")


# @spec AC-004: Record conditions
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-004
# @spec AC-006: Verify current PASS
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-006
def test_complete_pass_is_recorded_and_current(project: DeliveryProject) -> None:
    _prepare(project)
    code, payload = _record(project, "combined", report(SCOPE))
    assert (code, _codes(payload), payload["verdict"]) == (0, [], "PASS")
    assert _verify(project) == (0, [])
    # Traceability updates after the review never invalidate it.
    project.write(f".specs/features/{FEATURE}/changelog.md", "# Changelog\n\n- entry\n")
    assert _verify(project) == (0, [])
    project.write("calc.py", "def add(a, b):\n    return a + b + 0\n")
    assert _verify(project) == (1, ["scope_changed"])


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (report(["calc.py"]), ["scope_not_covered"]),
        (report(SCOPE, effort="medium"), ["reviewer_effort_not_high"]),
        (report(SCOPE, blocking=1), ["verdict_inconsistent"]),
        (report(SCOPE, failed_check=True), ["verdict_inconsistent"]),
        (report(SCOPE, verdict="BLOCKED"), ["verdict_inconsistent"]),
    ],
)
def test_invalid_reports_are_refused_and_write_nothing(
    project: DeliveryProject, payload: dict[str, object], expected: list[str]
) -> None:
    _prepare(project)
    code, result = _record(project, "combined", payload)
    assert (code, _codes(result)) == (1, expected)
    assert not (project.feature_dir / ".reviews" / "delivery.json").exists()


def test_record_requires_prepared_and_unchanged_scope(project: DeliveryProject) -> None:
    code, result = _record(project, "combined", report(SCOPE))
    assert (code, _codes(result)) == (1, ["scope_missing"])
    _prepare(project)
    project.write("calc.py", "def add(a, b):\n    return 5\n")
    code, result = _record(project, "combined", report(SCOPE))
    assert (code, _codes(result)) == (1, ["scope_changed"])


def test_invalid_report_file_or_kind_is_a_usage_error(project: DeliveryProject) -> None:
    _prepare(project)
    bad = project.root.parent / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    args = ["delivery", "review", "record", "--feature", FEATURE, "--report", str(bad)]
    assert project.run(*args, "--kind", "combined").exit_code == 2
    assert project.run(*args, "--kind", "style").exit_code == 2


# @spec AC-005: Round cap
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-005
def test_two_corrections_then_escalation(project: DeliveryProject) -> None:
    for round_number in range(1, 4):
        _prepare(project)
        code, result = _record(project, "combined", report(SCOPE, verdict="BLOCKED", blocking=1))
        assert (code, _codes(result)) == (1, ["review_blocked"]), round_number
        assert _verify(project)[1] == ["latest_round_blocked:combined"]
    before = (project.feature_dir / ".reviews" / "delivery.json").read_bytes()
    code, result = _record(project, "combined", report(SCOPE))
    assert (code, _codes(result)) == (1, ["round_cap_reached"])
    assert (project.feature_dir / ".reviews" / "delivery.json").read_bytes() == before


def test_a_pass_resets_the_round_count(project: DeliveryProject) -> None:
    _prepare(project)
    _record(project, "combined", report(SCOPE, verdict="BLOCKED", blocking=1))
    _record(project, "combined", report(SCOPE, verdict="BLOCKED", blocking=1))
    assert _record(project, "combined", report(SCOPE))[0] == 0
    for _ in range(3):
        assert _record(project, "combined", report(SCOPE, verdict="BLOCKED", blocking=1))[0] == 1
    assert _codes(_record(project, "combined", report(SCOPE))[1]) == ["round_cap_reached"]


def test_full_lane_requires_separate_review_and_audit(project: DeliveryProject) -> None:
    project.write(
        f".specs/features/{FEATURE}/spec.md",
        (project.feature_dir / "spec.md")
        .read_text()
        .replace("Medium criticality", "High criticality"),
    )
    _prepare(project)
    assert _record(project, "combined", report(SCOPE))[0] == 1  # spec.md joined the scope
    _prepare(project)
    scope = sorted([*SCOPE, f".specs/features/{FEATURE}/spec.md"])
    assert _record(project, "combined", report(scope))[0] == 0
    assert _verify(project) == (1, ["kind_missing:review", "kind_missing:audit"])
    assert _record(project, "review", report(scope))[0] == 0
    assert _verify(project) == (1, ["kind_missing:audit"])
    assert _record(project, "audit", report(scope))[0] == 0
    assert _verify(project) == (1, ["reviewers_not_independent"])
    assert _record(project, "audit", report(scope, agent="auditor"))[0] == 0
    assert _verify(project) == (0, [])


def test_light_lane_accepts_review_and_audit_after_a_blocked_combined(
    project: DeliveryProject,
) -> None:
    _prepare(project)
    _record(project, "combined", report(SCOPE, verdict="BLOCKED", blocking=1))
    assert _record(project, "review", report(SCOPE))[0] == 0
    assert _record(project, "audit", report(SCOPE, agent="auditor"))[0] == 0
    assert _verify(project) == (0, [])


def test_edited_receipt_is_not_trusted(project: DeliveryProject) -> None:
    _prepare(project)
    _record(project, "combined", report(SCOPE, verdict="BLOCKED", blocking=1))
    path = project.feature_dir / ".reviews" / "delivery.json"
    data = json.loads(path.read_text())
    data["kinds"]["combined"]["rounds"][-1]["verdict"] = "PASS"
    path.write_text(json.dumps(data))
    assert _verify(project) == (1, ["latest_round_blocked:combined"])
    forged = json.dumps(report(SCOPE))
    data["kinds"]["combined"]["rounds"][-1]["report_raw"] = forged
    path.write_text(json.dumps(data))
    assert _verify(project) == (1, ["receipt_invalid:combined"])
    data["kinds"]["combined"]["rounds"][-1]["files"]["calc.py"] = "0" * 64
    data["kinds"] = []
    path.write_text(json.dumps(data))
    assert _verify(project) == (1, ["no_receipt"])


def test_lifecycle_status_change_keeps_the_review_current(project: DeliveryProject) -> None:
    _prepare(project)
    spec = project.feature_dir / "spec.md"
    assert _record(project, "combined", report(SCOPE))[0] == 0
    spec.write_text(spec.read_text().replace("**Status:** Planned", "**Status:** Implemented"))
    assert _verify(project) == (0, [])
    spec.write_text(spec.read_text().replace("their sum", "their product"))
    assert _verify(project)[0] == 1  # A normative change invalidates the review.


def test_verify_without_receipt(project: DeliveryProject) -> None:
    assert _verify(project) == (1, ["no_receipt"])

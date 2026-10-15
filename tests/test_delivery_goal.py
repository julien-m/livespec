"""Delivery lane and delivery.review task in the implement goal (feature 086 AC-007)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from tests.delivery_support import FEATURE, MODEL, DeliveryProject, git, make_project, report
from validator.cli import app
from validator.goal_generic_evidence import (
    _delivery_review_missing_items,  # pyright: ignore[reportPrivateUsage]
)

ROOT = Path(__file__).resolve().parents[1]


def _render(command: str, feature: str | None, flags: str) -> dict[str, Any]:
    args = ["goal", "render", command, "--flags", flags, "--json"]
    if feature:
        args[3:3] = ["--feature", feature]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["canonical"]


def _task_ids(canonical: dict[str, Any]) -> list[str]:
    return [str(task["id"]) for task in cast(list[dict[str, Any]], canonical["tasks"])]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DeliveryProject:
    project = make_project(tmp_path)
    monkeypatch.chdir(project.root)
    return project


# @spec AC-007: Lane and delivery.review in the implement goal
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-007
def test_light_goal_has_lane_rows_and_delivery_task(project: DeliveryProject) -> None:
    project.review_spec()
    canonical = _render("spec-implement", FEATURE, f"--model={MODEL}")
    runtime = canonical["runtime_context"]
    assert runtime["delivery_lane"]["lane"] == "light"
    rows = " ".join(map(str, canonical["execution_tasks"]))
    assert "one independent native `combined` reviewer" in rows
    assert "two independent native reviewers" not in rows
    ids = _task_ids(canonical)
    assert "delivery.review" in ids
    assert ids[-2:] == ["outcome.verified", "archive.run"]
    assert len(ids) <= 10


def test_full_goal_has_full_rows(project: DeliveryProject) -> None:
    canonical = _render("spec-implement", FEATURE, f"--model={MODEL}")
    assert canonical["runtime_context"]["delivery_lane"]["lane"] == "full"
    rows = " ".join(map(str, canonical["execution_tasks"]))
    assert "two independent native reviewers" in rows
    assert "delivery.review" in _task_ids(canonical)


def test_other_goals_are_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    for command, feature, flags in (
        ("spec-fix", "084-bugfix-lane", "--auto"),
        ("spec-plan", "084-bugfix-lane", "--auto --model=m"),
        ("spec-implement", None, "--model=m"),
    ):
        canonical = _render(command, feature, flags)
        assert "delivery_lane" not in canonical["runtime_context"]
        assert "delivery.review" not in _task_ids(canonical)


def test_goal_accepts_only_a_current_passing_receipt(project: DeliveryProject) -> None:
    project.review_spec()
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "reviewed")
    project.write("calc.py", "def add(a, b):\n    return b + a\n")
    task = {"expected_evidence": {"feature_slug": FEATURE, "reviewer_model": MODEL}}
    receipt = f".specs/features/{FEATURE}/.reviews/delivery.json"

    def missing(path: str = receipt) -> list[str]:
        evidence = {"delivery_review_receipt_path": path}
        return _delivery_review_missing_items(
            task, evidence, contract={}, project_root=project.root
        )

    assert missing() == ["delivery_review_receipt_valid:no_receipt"]
    project.run(
        "delivery", "review", "prepare", "--feature", FEATURE, "--base", "HEAD~1", "--model", MODEL
    )
    report_path = project.root.parent / "report.json"
    report_path.write_text(json.dumps(report(["calc.py"])), encoding="utf-8")
    args = ["--feature", FEATURE, "--kind", "combined", "--report", str(report_path)]
    assert project.run("delivery", "review", "record", *args).exit_code == 0
    assert missing() == []
    assert missing("elsewhere.json")[0].startswith("delivery_review_receipt_valid:not_the")
    project.write("calc.py", "def add(a, b):\n    return 0\n")
    assert missing() == ["delivery_review_receipt_valid:scope_changed"]

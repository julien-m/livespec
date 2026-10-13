"""The delivery review base precedes every feature change (feature 086 AC-003, AC-004)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from tests.delivery_support import FEATURE, MODEL, DeliveryProject, git, make_project, report
from validator.delivery.review_scope import current_scope

SPEC = f".specs/features/{FEATURE}/spec.md"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DeliveryProject:
    """The spec is committed together with code, the usual layout of a feature commit."""
    project = make_project(tmp_path)
    git(project.root, "reset", "-q", "--soft", "HEAD~1")
    project.write("calc.py", "def add(a, b):\n    return a - b\n")
    project.review_spec()
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "spec and code")
    monkeypatch.chdir(project.root)
    return project


def _prepare(project: DeliveryProject, base: str) -> tuple[int, dict[str, object]]:
    return project.json(
        "delivery", "review", "prepare", "--feature", FEATURE, "--base", base, "--model", MODEL
    )


def _record(project: DeliveryProject, kind: str, files: list[str], agent: str) -> list[str]:
    path = project.root.parent / f"report-{kind}.json"
    path.write_text(json.dumps(report(files, agent=agent)), encoding="utf-8")
    payload = project.json(
        "delivery", "review", "record", "--feature", FEATURE, "--kind", kind, "--report", str(path)
    )[1]
    return [r["code"] for r in cast(list[dict[str, Any]], payload["reasons"])]


def _verify(project: DeliveryProject) -> list[str]:
    args = ("delivery", "review", "verify", "--feature", FEATURE, "--model", MODEL)
    payload = project.json(*args)[1]
    return [r["code"] for r in cast(list[dict[str, Any]], payload["reasons"])]


# @spec AC-003: Scope of the complete diff
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-003
def test_commit_creating_spec_and_code_is_not_a_base(project: DeliveryProject) -> None:
    code, scope = _prepare(project, "HEAD")
    assert (code, scope["error"]) == (1, "base_not_feature_start")
    code, scope = _prepare(project, "HEAD~1")
    assert code == 0 and "calc.py" in cast(dict[str, str], scope["files"])


def test_uncommitted_spec_has_no_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = make_project(tmp_path)
    git(project.root, "reset", "-q", "--soft", "HEAD~1")
    git(project.root, "rm", "-rq", "--cached", f".specs/features/{FEATURE}")
    project.write("calc.py", "def add(a, b):\n    return 0\n")
    git(project.root, "commit", "-qam", "code")
    monkeypatch.chdir(project.root)
    code, scope = _prepare(project, "HEAD")
    assert (code, scope["error"]) == (1, "base_not_feature_start")
    assert "not committed" in str(scope["detail"])


# @spec AC-004: Record conditions
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-004
def test_edited_base_is_refused_by_record_and_verify(project: DeliveryProject) -> None:
    assert _prepare(project, "HEAD~1")[0] == 0
    scope_file = project.feature_dir / ".reviews" / "delivery-scope.json"
    good = json.loads(scope_file.read_text())
    files = sorted(cast(dict[str, str], good["files"]))
    head = git(project.root, "rev-parse", "HEAD").strip()
    forged = {**good, "base_commit": head, "files": current_scope(project.root, head)}
    scope_file.write_text(json.dumps(forged))
    assert _record(project, "review", files, "reviewer") == ["base_not_feature_start"]
    scope_file.write_text(json.dumps(good))
    assert _record(project, "review", files, "reviewer") == []
    assert _record(project, "audit", files, "auditor") == []
    receipt = project.feature_dir / ".reviews" / "delivery.json"
    data = json.loads(receipt.read_text())
    data["kinds"]["audit"]["rounds"][-1]["base_commit"] = head
    receipt.write_text(json.dumps(data))
    assert _verify(project) == ["base_not_feature_start"]


def test_submodule_pointer_is_part_of_the_identity(project: DeliveryProject) -> None:
    head = git(project.root, "rev-parse", "HEAD").strip()
    base = git(project.root, "rev-parse", "HEAD~1").strip()
    git(project.root, "update-index", "--add", "--cacheinfo", f"160000,{head},sub")
    (project.root / "sub").mkdir()
    before = current_scope(project.root, base)["sub"]
    git(project.root, "update-index", "--cacheinfo", f"160000,{base},sub")
    assert before == f"gitlink:{head}" != current_scope(project.root, base)["sub"]

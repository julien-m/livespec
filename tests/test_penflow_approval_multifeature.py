"""Real cumulative approval files; reviewer responses are explicit protocol fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.penflow_approval_fixtures import canonical_approval_contract
from tests.test_penflow_review_approval import (
    FEATURE,
    ReviewProject,
    _read_json,
    _reference,
    _write_json,
)
from tests.test_penflow_review_approval import (
    project as project,
)
from validator.locks import acquire_lock
from validator.penflow_approval_files import PenflowApprovalError
from validator.penflow_requirement_source import (
    extract_requirement_definitions,
    semantic_source_sha256,
)
from validator.penflow_review_approval import approve_review_result, require_approved_requirements
from validator.penflow_review_snapshot import create_review_snapshot

SECOND = "002-notifications"


def _feature_file(project: ReviewProject, slug: str, filename: str) -> Path:
    return project.root / ".specs/features" / slug / filename


def _add_second(project: ReviewProject) -> None:
    spec = _feature_file(project, SECOND, "spec.md")
    spec.parent.mkdir()
    spec.write_text(project.spec.read_text().replace("Save profile", "Notification preferences"))
    spec.with_name("plan.md").write_text("# Plan\n\nUse the notification settings adapter.\n")


def _canonical_contract_fixture(project: ReviewProject, active: list[str]) -> None:
    """Write explicit global C20 mappings, retaining approved raw lifecycle identities."""
    prior = _read_json(project.baseline)["sources"] if project.baseline.exists() else []
    records = {item["path"]: item for item in prior}
    refs: list[dict[str, str]] = []
    bindings: list[dict[str, str]] = []
    for slug in sorted(active):
        spec = _feature_file(project, slug, "spec.md")
        ref = _reference(project.root, spec)
        old = records.get(ref["path"])
        if old and old["semantic_sha256"] == semantic_source_sha256(spec):
            ref["sha256"] = old["sha256"]
        refs.append(ref)
        bindings.extend(
            {"requirement_id": item.id, "obligation_id": slug}
            for item in extract_requirement_definitions(spec, slug)
        )
    _write_json(project.contract, canonical_approval_contract(refs, bindings, sorted(active)))


def _approve_protocol_fixture(project: ReviewProject, slug: str) -> dict[str, Any]:
    snapshot = create_review_snapshot(project.root, slug)
    result = project.result(snapshot)
    with acquire_lock(project.root / ".specs"):
        baseline = approve_review_result(project.root, slug, result)
    _feature_file(project, slug, "pipeline.md").write_text(
        "| Phase | Status |\n| Plan Review | Done |\n"
    )
    return baseline


def _two_approved(project: ReviewProject) -> dict[str, Any]:
    _canonical_contract_fixture(project, [FEATURE])
    _approve_protocol_fixture(project, FEATURE)
    _add_second(project)
    _canonical_contract_fixture(project, [FEATURE, SECOND])
    return _approve_protocol_fixture(project, SECOND)


def _retire(project: ReviewProject, slug: str, remaining: list[str]) -> dict[str, Any]:
    spec = _feature_file(project, slug, "spec.md")
    spec.write_text(spec.read_text().replace("visual: true", "visual: false"))
    _canonical_contract_fixture(project, remaining)
    return _approve_protocol_fixture(project, slug)


# @spec AC-008: cumulative source selection and independently governed retirement
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-008
@pytest.mark.parametrize("order", [(FEATURE, SECOND), (SECOND, FEATURE)])
def test_approval_accumulates_sorted_sources_and_all_plans(
    project: ReviewProject, order: tuple[str, str]
) -> None:
    _add_second(project)
    _canonical_contract_fixture(project, [order[0]])
    _approve_protocol_fixture(project, order[0])
    _canonical_contract_fixture(project, list(order))
    baseline = _approve_protocol_fixture(project, order[1])
    assert baseline["selection"] == [FEATURE, SECOND]
    assert baseline["retired_features"] == []
    assert len(baseline["projection"]["requirements"]) == 8
    assert {item["obligation_id"] for item in baseline["projection"]["bindings"]} == {
        FEATURE,
        SECOND,
    }
    approval = _read_json(project.root / baseline["approval_receipts"][0]["path"])
    assert [item["path"] for item in approval["inputs"]["plans"]] == [
        f".specs/features/{slug}/plan.md" for slug in [FEATURE, SECOND]
    ]
    for slug in order:
        require_approved_requirements(project.root, slug)


def test_retirement_keeps_other_feature_and_reactivation_restores_union(
    project: ReviewProject,
) -> None:
    _two_approved(project)
    retired = _retire(project, FEATURE, [SECOND])
    assert retired["selection"] == [FEATURE, SECOND]
    assert retired["retired_features"] == [FEATURE]
    assert retired["disposition"] == "active"
    assert len(retired["projection"]["requirements"]) == 4
    assert all(
        item["id"].startswith(f"livespec:{SECOND}:")
        for item in retired["projection"]["requirements"]
    )
    require_approved_requirements(project.root, FEATURE, disposition="retired")
    require_approved_requirements(project.root, SECOND)
    with pytest.raises(PenflowApprovalError, match="disposition_mismatch"):
        require_approved_requirements(project.root, FEATURE)
    project.spec.write_text(project.spec.read_text().replace("visual: false", "visual: true"))
    _canonical_contract_fixture(project, [FEATURE, SECOND])
    active = _approve_protocol_fixture(project, FEATURE)
    assert active["retired_features"] == []
    assert len(active["projection"]["requirements"]) == 8
    for slug in [FEATURE, SECOND]:
        require_approved_requirements(project.root, slug)


def test_all_retired_has_empty_projection_and_preserves_governed_membership(
    project: ReviewProject,
) -> None:
    _two_approved(project)
    _retire(project, FEATURE, [SECOND])
    baseline = _retire(project, SECOND, [])
    assert baseline["selection"] == baseline["retired_features"] == [FEATURE, SECOND]
    assert baseline["disposition"] == "retired"
    assert baseline["projection"] == {
        "source_kind": "livespec-fr-ac-v1",
        "sources": [],
        "requirements": [],
        "bindings": [],
        "uncovered": [],
    }
    for slug in [FEATURE, SECOND]:
        require_approved_requirements(project.root, slug, disposition="retired")
        with pytest.raises(PenflowApprovalError, match="disposition_mismatch"):
            require_approved_requirements(project.root, slug)


def test_draft_backlog_is_not_part_of_cumulative_selection(project: ReviewProject) -> None:
    backlog = _feature_file(project, "999-backlog", "spec.md")
    backlog.parent.mkdir()
    backlog.write_text("---\nstatus: Draft\nvisual: true\n---\n# Incomplete backlog\n")
    baseline = _two_approved(project)
    assert baseline["selection"] == [FEATURE, SECOND]
    require_approved_requirements(project.root, SECOND)
    with pytest.raises(PenflowApprovalError, match="selection_or_scope_mismatch"):
        require_approved_requirements(project.root, "999-backlog")


def test_other_feature_plan_mutation_blocks_current_feature(project: ReviewProject) -> None:
    _two_approved(project)
    project.plan.write_text(project.plan.read_text() + "\nUse a different persistence model.\n")
    with pytest.raises(PenflowApprovalError, match="semantics_changed"):
        require_approved_requirements(project.root, SECOND)


def test_contract_cannot_select_only_new_feature(project: ReviewProject) -> None:
    _approve_protocol_fixture(project, FEATURE)
    old = project.baseline.read_bytes()
    _add_second(project)
    _canonical_contract_fixture(project, [SECOND])
    with pytest.raises(PenflowApprovalError, match="canonical_source_selection_mismatch"):
        create_review_snapshot(project.root, SECOND)
    assert project.baseline.read_bytes() == old


def test_lifecycle_change_keeps_prior_raw_source_when_adding_feature(
    project: ReviewProject,
) -> None:
    first = _approve_protocol_fixture(project, FEATURE)
    project.spec.write_text(
        project.spec.read_text().replace("status: Approved", "status: Implemented")
    )
    assert _reference(project.root, project.spec)["sha256"] != first["sources"][0]["sha256"]
    _add_second(project)
    _canonical_contract_fixture(project, [FEATURE, SECOND])
    second = _approve_protocol_fixture(project, SECOND)
    assert second["sources"][0] == first["sources"][0]
    for slug in [FEATURE, SECOND]:
        require_approved_requirements(project.root, slug)


@pytest.mark.parametrize("pending", [FEATURE, SECOND])
def test_every_active_feature_requires_completed_plan_review(
    project: ReviewProject, pending: str
) -> None:
    _two_approved(project)
    _feature_file(project, pending, "pipeline.md").write_text("| Plan Review | Pending |\n")
    for slug in [FEATURE, SECOND]:
        with pytest.raises(PenflowApprovalError, match="plan_review_not_completed"):
            require_approved_requirements(project.root, slug)


@pytest.mark.parametrize("missing", ["previous_baseline", "first_approval", "first_review_output"])
def test_missing_prior_history_cannot_revalidate_or_start_new_adoption(
    project: ReviewProject, missing: str
) -> None:
    latest = _two_approved(project)
    previous_path = project.root / latest["previous"]["path"]
    previous = _read_json(previous_path)
    approval_path = project.root / previous["approval_receipts"][0]["path"]
    approval = _read_json(approval_path)
    target = {
        "previous_baseline": previous_path,
        "first_approval": approval_path,
        "first_review_output": project.root / approval["review"]["output"]["path"],
    }[missing]
    target.unlink()
    baseline_bytes = project.baseline.read_bytes()
    with pytest.raises((PenflowApprovalError, OSError)):
        require_approved_requirements(project.root, SECOND)
    with pytest.raises((PenflowApprovalError, OSError)):
        create_review_snapshot(project.root, SECOND)
    assert project.baseline.read_bytes() == baseline_bytes

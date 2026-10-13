"""Capped spec and plan reviews: blockers only, carry-over and round cap (feature 088)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.delivery_support import FEATURE, MODEL, DeliveryProject, make_project, spec_text
from validator.clarify_gate import scan_clarification_opportunities
from validator.semantic.review_context import PreparedReview
from validator.semantic.review_contract import (
    ReviewReceipt,
    ScopeFinding,
    carry_over,
    validate_review_result,
)
from validator.semantic.review_files import prepare_feature_review
from validator.semantic.review_rounds import rounds_path


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DeliveryProject:
    project = make_project(tmp_path)
    monkeypatch.chdir(project.root)
    return project


def _raw(
    project: DeliveryProject,
    *,
    disposition: str = "covered",
    ambiguity: bool | None = None,
    scope: dict[str, object] | None = None,
    finding: str | None = None,
) -> tuple[PreparedReview, str]:
    prepared = prepare_feature_review(project.root, FEATURE, "spec", MODEL)
    sections = {s.section_id: s for s in prepared.sections}
    first = prepared.requirements[0]
    citation = {"section_id": first.section_ids[0], "excerpt": sections[first.section_ids[0]].text}
    conclusions = [
        {
            "requirement_id": r.requirement_id,
            "disposition": disposition if r is first else "covered",
            "rationale": "Independent judgment.",
            "source_citations": [
                {"section_id": r.section_ids[0], "excerpt": sections[r.section_ids[0]].text}
            ],
        }
        for r in prepared.requirements
    ]
    ambiguities = []
    if ambiguity is not None:
        ambiguities.append(
            {
                "requirement_id": first.requirement_id,
                "decision_key": "rounding",
                "question": "Round half up or half even?",
                "critical": ambiguity,
                "citations": [citation],
            }
        )
    findings = []
    if finding:
        findings.append(
            {
                "category": "testability",
                "severity": finding,
                "description": "Name the overflow behaviour.",
                "suggestion": "Add an edge case.",
                "citations": [citation],
            }
        )
    raw = json.dumps(
        {
            "batch_id": prepared.batches[0].batch_id,
            "reviewed_section_ids": list(prepared.batches[0].section_ids),
            "conclusions": conclusions,
            "ambiguities": ambiguities,
            "extra_scope": [{**scope, "citations": [citation]}] if scope else [],
            "findings": findings,
            "confidence": 5,
        }
    )
    return prepared, raw


def _ready(project: DeliveryProject, **options: Any) -> ReviewReceipt:
    prepared, raw = _raw(project, **options)
    receipt = validate_review_result(prepared, [raw])
    assert receipt.complete, receipt.errors
    return receipt


# @spec AC-001: Non-critical ambiguity and warnings do not block
#   — .specs/features/088-capped-reviews/spec.md#ac-001
def test_non_critical_ambiguity_and_warnings_are_ready_and_carried(
    project: DeliveryProject,
) -> None:
    receipt = _ready(project, disposition="ambiguous", ambiguity=False, finding="warning")
    assert receipt.ready
    assert carry_over(receipt) == [
        "warning: testability: Name the overflow behaviour.",
        f"ambiguity: {FEATURE}:AC-001: Round half up or half even?",
    ]


@pytest.mark.parametrize(
    "options",
    [
        {"disposition": "ambiguous", "ambiguity": True},
        {"disposition": "ambiguous"},
        {"disposition": "missing"},
        {"finding": "blocking"},
    ],
)
def test_blockers_still_block(project: DeliveryProject, options: dict[str, object]) -> None:
    assert not _ready(project, **options).ready


@pytest.mark.parametrize(
    ("scope", "ready"),
    [
        ({"kind": "technical", "justification": "Atomic write.", "approved": False}, True),
        ({"kind": "technical", "justification": " ", "approved": False}, False),
        ({"kind": "business", "justification": "Nice.", "approved": False}, False),
        ({"justification": "Legacy reviewer output.", "approved": False}, False),
    ],
)
def test_scope_kind_decides_approval(
    project: DeliveryProject, scope: dict[str, object], ready: bool
) -> None:
    receipt = _ready(project, scope={"description": "Temp file then rename.", **scope})
    assert receipt.ready is ready
    if ready:
        assert carry_over(receipt) == ["technical scope: Temp file then rename.: Atomic write."]


# @spec AC-002: Justified technical necessity is approved
#   — .specs/features/088-capped-reviews/spec.md#ac-002
def test_legacy_scope_without_kind_is_business() -> None:
    finding = ScopeFinding.model_validate(
        {"description": "d", "justification": "j", "approved": True, "citations": []}
        | {"citations": [{"section_id": "s", "excerpt": "e"}]}
    )
    assert finding.kind == "business"


def _ingest(project: DeliveryProject, **options: Any) -> tuple[int, dict[str, object]]:
    _, raw = _raw(project, **options)
    bundle = project.root.parent / "bundle.json"
    bundle.write_text(json.dumps({"raw_results": [raw], "synthesis": None}), encoding="utf-8")
    result = project.run(
        "validate",
        str(project.feature_dir),
        "--ingest-review",
        str(bundle),
        "--review-kind",
        "spec",
        "--model",
        MODEL,
    )
    return result.exit_code, json.loads(result.output.strip().splitlines()[-1])


# @spec AC-003: Round number, cap and carry-over at ingestion
#   — .specs/features/088-capped-reviews/spec.md#ac-003
def test_third_blocked_round_reaches_the_cap(project: DeliveryProject) -> None:
    rounds = []
    for index in range(3):
        project.write(
            f".specs/features/{FEATURE}/spec.md",
            spec_text().replace("their sum", f"their sum (revision {index})"),
        )
        code, payload = _ingest(project, finding="blocking")
        assert code == 1
        rounds.append((payload["round"], payload["round_cap_reached"]))
    assert rounds == [(1, False), (2, False), (3, True)]
    assert _ingest(project, finding="blocking")[1]["round"] == 3  # Same state, same round.
    code, payload = _ingest(project, finding="warning")
    assert code == 0
    assert payload["round"] == 3 and payload["round_cap_reached"] is False
    assert payload["carry_over"] == ["warning: testability: Name the overflow behaviour."]
    ledger = json.loads(rounds_path(project.root, FEATURE, "spec").read_text())
    assert [item["ready"] for item in ledger["rounds"]] == [False, False, True]


def test_ready_review_resets_the_count(project: DeliveryProject) -> None:
    assert _ingest(project)[1]["round"] == 1
    project.write(f".specs/features/{FEATURE}/spec.md", spec_text().replace("sum", "total"))
    code, payload = _ingest(project, finding="blocking")
    assert (code, payload["round"], payload["round_cap_reached"]) == (1, 1, False)


# @spec AC-004: An isolated qualitative word does not block
#   — .specs/features/088-capped-reviews/spec.md#ac-004
def test_vague_word_is_reported_but_never_critical(tmp_path: Path) -> None:
    spec = tmp_path / "001-x" / "spec.md"
    spec.parent.mkdir()
    spec.write_text("### FR-001\nThe export must be fast and secure.\n[NEEDS CLARIFICATION] who?\n")
    items = scan_clarification_opportunities(spec)
    vague = [item for item in items if item.category == "non-functional quality"]
    assert vague and not any(item.critical for item in vague)
    assert any(item.critical for item in items if item not in vague)


def test_documentary_acceptance_still_requires_covered(tmp_path: Path) -> None:
    from tests.acceptance_review_support import add_documentary_acceptance
    from tests.review_support import grounded_response, reviewed_project
    from validator.semantic.acceptance_review import (
        ingest_acceptance_review,
        prepare_acceptance_review,
        verify_acceptance_review,
    )

    feature = "001-test"
    reviewed_project(tmp_path, feature)
    receipt = add_documentary_acceptance(tmp_path, feature)
    assert verify_acceptance_review(tmp_path, feature, receipt, model="reviewer/v1")
    prepared = prepare_acceptance_review(tmp_path, feature, "reviewer/v1")
    raw = json.loads(grounded_response(prepared))
    first = raw["conclusions"][0]
    first["disposition"] = "ambiguous"
    raw["ambiguities"] = [
        {
            "requirement_id": first["requirement_id"],
            "decision_key": "scope",
            "question": "Which sections?",
            "critical": False,
            "citations": first["source_citations"],
        }
    ]
    ingested, path = ingest_acceptance_review(
        tmp_path, feature, [json.dumps(raw)], model="reviewer/v1"
    )
    assert not ingested.ready and "acceptance_requires_covered" in ingested.errors
    assert not verify_acceptance_review(tmp_path, feature, path, model="reviewer/v1")


def test_plan_analysis_reports_only_blockers(project: DeliveryProject) -> None:
    from validator.semantic.review_contract import RequirementConclusion, conclusion_blocks

    ambiguous = RequirementConclusion.model_validate(
        {
            "requirement_id": f"{FEATURE}:AC-001",
            "disposition": "ambiguous",
            "rationale": "r",
            "source_citations": [{"section_id": "s", "excerpt": "e"}],
        }
    )
    receipt = _ready(project, disposition="ambiguous", ambiguity=False)
    assert not conclusion_blocks(ambiguous, receipt.ambiguities)
    assert conclusion_blocks(ambiguous, [])

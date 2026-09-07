"""Build current grounded test review evidence at the external reviewer boundary."""

from __future__ import annotations

import json
from pathlib import Path

from validator.semantic.review_api import ingest_feature_review, prepare_feature_review


def grounded_response(prepared) -> str:
    """Return an independent reviewer fake grounded in all submitted sections."""
    assert len(prepared.batches) == 1
    batch = prepared.batches[0]
    sections = {section.section_id: section for section in prepared.sections}
    plan = [section for section in prepared.sections if section.role == "plan"]
    conclusions = []
    for requirement in prepared.requirements:
        source = sections[requirement.section_ids[0]]
        conclusions.append(
            {
                "requirement_id": requirement.requirement_id,
                "disposition": "covered",
                "rationale": "Required outcome is represented in this fixture.",
                "source_citations": [{"section_id": source.section_id, "excerpt": source.text}],
                "plan_citations": [
                    {"section_id": section.section_id, "excerpt": section.text} for section in plan
                ],
                "searched_plan_sections": [],
            }
        )
    return json.dumps(
        {
            "batch_id": batch.batch_id,
            "reviewed_section_ids": list(batch.section_ids),
            "conclusions": conclusions,
            "ambiguities": [],
            "extra_scope": [],
            "findings": [],
            "confidence": 5,
        }
    )


def reviewed_project(root: Path, feature: str = "001-test") -> Path:
    """Create minimal genuine files with both current complete fake-provider receipts."""
    directory = root / ".specs/features" / feature
    directory.mkdir(parents=True, exist_ok=True)
    (root / ".specs/stacks").mkdir(exist_ok=True)
    (root / ".specs/semantic").mkdir(exist_ok=True)
    (root / ".specs/semantic/config.yaml").write_text("review_model: reviewer/v1\n")
    for name, text in [
        ("constitution.md", "Local execution."),
        ("project.md", "CLI exports."),
        ("stacks/_default.md", "Python."),
    ]:
        (root / ".specs" / name).write_text(text)
    (directory / "spec.md").write_text(
        "---\nvisual: false\nstatus: Approved\n---\n# Export\n## FR-001\n"
        "Delete expired files after 24 hours.\n## AC-001\nExpired files are absent.\n"
    )
    (directory / "plan.md").write_text(
        "# Plan\nFR-001 AC-001 Delete files once older than 24 hours.\n"
    )
    for kind in ("spec", "plan"):
        prepared = prepare_feature_review(root, feature, kind)
        receipt, _ = ingest_feature_review(root, feature, kind, [grounded_response(prepared)])
        assert receipt.complete and receipt.ready, receipt.errors
    return directory


def review_existing_project(root: Path, feature: str) -> None:
    """Add current transport-fake reviews without replacing another fixture's governed files."""
    directory = root / ".specs/features" / feature
    for name, text in [
        ("constitution.md", "Local execution."),
        ("project.md", "Feature fixture."),
        ("stacks/_default.md", "Python."),
        ("semantic/config.yaml", "review_model: reviewer/v1\n"),
    ]:
        path = root / ".specs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(text)
    if not (directory / "plan.md").exists():
        (directory / "plan.md").write_text("# Plan\nImplement the declared contract.\n")
    for kind in ("spec", "plan"):
        prepared = prepare_feature_review(root, feature, kind)
        receipt, _ = ingest_feature_review(root, feature, kind, [grounded_response(prepared)])
        assert receipt.complete and receipt.ready, receipt.errors

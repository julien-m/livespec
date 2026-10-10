"""Shared real-run project and acceptance-review fixtures for execution evidence tests."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest

from validator.drivers.runner import run_capability
from validator.drivers.schemas import DriverCapability, DriverManifest
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.execution_scope import digest
from validator.semantic.review_context import PreparedReview

FEATURE = "001-add"
AC = f"{FEATURE}:AC-001"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    feature = tmp_path / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Addition\nAC-001: Adding one and two returns three.\n")
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_app.py").write_text(
        "from app import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    )
    mapping = {
        "schema_version": "1",
        "feature": FEATURE,
        "reviewer_model": "independent-test-review-fixture",
        "review_receipt_path": "acceptance-review.json",
        "bindings": [
            {
                "requirement_id": AC,
                "test_id": "test_app::test_add",
                "expected": "Adding one and two returns three",
                "assertion_path": "test_app.py",
                "start_line": 4,
                "end_line": 4,
                "source_sha256": digest((tmp_path / "test_app.py").read_bytes()),
                "justification": "The assertion calls add(1, 2) and compares its result to three.",
            }
        ],
    }
    (tmp_path / "mapping.json").write_text(json.dumps(mapping))
    prepared = prepare_mapping_review(tmp_path, FEATURE, tmp_path / "mapping.json")
    raw = _review_response(prepared)
    receipt = ingest_mapping_review(prepared, [raw], tmp_path / "acceptance-review.json")
    assert receipt.ready, receipt.errors
    return tmp_path


def _review_response(prepared: PreparedReview) -> str:
    """Supply the grounded transport fixture for the real subprocess project."""
    spec_section = next(section for section in prepared.sections if section.role == "spec")
    test_section = next(section for section in prepared.sections if section.source == "test_app.py")
    return json.dumps(
        {
            "batch_id": prepared.batches[0].batch_id,
            "reviewed_section_ids": [section.section_id for section in prepared.sections],
            "conclusions": [
                {
                    "requirement_id": AC,
                    "disposition": "covered",
                    "rationale": "Adding one and two returns three is directly compared.",
                    "source_citations": [
                        {
                            "section_id": spec_section.section_id,
                            "excerpt": "AC-001: Adding one and two returns three.",
                        }
                    ],
                    "plan_citations": [
                        {"section_id": test_section.section_id, "excerpt": "assert add(1, 2) == 3"}
                    ],
                }
            ],
            "ambiguities": [],
            "extra_scope": [],
            "findings": [],
            "confidence": 5,
        }
    )


def run(project: Path, command: str | None = None, *, mapping: str = "mapping.json") -> Path:
    driver = DriverManifest(
        name="pytest",
        snapshots=DriverCapability(
            command=command or f"{shlex.quote(sys.executable)} -m pytest test_app.py -q",
            report_adapter="junit",
            acceptance_mapping=mapping,
        ),
    )
    result = run_capability(driver, "snapshots", project_root=project, feature=FEATURE)
    assert result.execution_receipt_path
    return Path(result.execution_receipt_path)

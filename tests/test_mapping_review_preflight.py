"""Mapping mistakes fail before expensive execution, retaining exact review evidence."""

# @spec(FR-009)
# @spec(FR-010)

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.execution_evidence_support import AC, FEATURE, _review_response, run
from tests.execution_evidence_support import project as project
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.execution_scope import digest


def _two_assertions(project: Path) -> Path:
    test = project / "test_app.py"
    test.write_text(test.read_text() + "    assert add(1, 2) != 4\n")
    path = project / "mapping.json"
    mapping = json.loads(path.read_text())
    first = mapping["bindings"][0]
    first["source_sha256"] = digest(test.read_bytes())
    mapping["bindings"].append(first | {"start_line": 5, "end_line": 5})
    path.write_text(json.dumps(mapping))
    return path


def test_representative_citation_cannot_mark_all_bindings_ready_before_execution(project):
    path = _two_assertions(project)
    prepared = prepare_mapping_review(project, FEATURE, path)
    destination = project / "acceptance-review.json"
    receipt = ingest_mapping_review(prepared, [_review_response(prepared)], destination)
    assert not receipt.ready and not receipt.complete
    assert any("ungrounded_acceptance_binding" in error for error in receipt.errors)
    assert json.loads(destination.read_text())["ready"] is False
    assert not (project / ".specs/.execution").exists()
    raw = json.loads(_review_response(prepared))
    section = next(s for s in prepared.sections if s.source == "test_app.py")
    raw["conclusions"][0]["plan_citations"][0]["excerpt"] = section.text
    corrected = ingest_mapping_review(prepared, [json.dumps(raw)], destination)
    assert corrected.ready and corrected.complete
    verified = verify_execution_receipt(run(project), project, FEATURE)
    assert verified.valid and verified.certified_acs == [AC]


def test_multiple_assertions_in_one_binding_fail_during_review_preparation(project):
    path = _two_assertions(project)
    mapping = json.loads(path.read_text())
    mapping["bindings"][0]["end_line"] = 5
    path.write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match="Binding does not cite an assertion"):
        prepare_mapping_review(project, FEATURE, path)
    assert not (project / ".specs/.execution").exists()

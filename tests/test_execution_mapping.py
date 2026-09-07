"""Exact acceptance mapping scope, review identity and concurrent-input checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review


def test_acceptance_mapping_budget_is_explicit_bounded_and_fingerprint_bound(project: Path) -> None:
    from validator.semantic.review_receipts import verify_review_receipt

    path = project / "mapping.json"
    previous = prepare_mapping_review(project, FEATURE, path)
    assert previous.max_chars == 60000
    mapping = json.loads(path.read_text())
    mapping["review_max_chars"] = 200000
    path.write_text(json.dumps(mapping))
    enlarged = prepare_mapping_review(project, FEATURE, path)
    assert enlarged.max_chars == 200000 and enlarged.complete
    assert enlarged.context_hash != previous.context_hash
    assert not verify_review_receipt(project / "acceptance-review.json", enlarged)
    mapping["review_max_chars"] = 200001
    path.write_text(json.dumps(mapping))
    with pytest.raises(ValueError):
        prepare_mapping_review(project, FEATURE, path)


def _capture_cached_mapping(project: Path) -> tuple[Path, Path, Path]:
    cache = project / ".specs/features" / FEATURE / ".reviews"
    cache.mkdir()
    mapping_path = cache / "acceptance-mapping.json"
    review_path = cache / "acceptance-review.json"
    mapping = json.loads((project / "mapping.json").read_text())
    mapping["review_receipt_path"] = review_path.relative_to(project).as_posix()
    mapping_path.write_text(json.dumps(mapping))
    prepared = prepare_mapping_review(project, FEATURE, mapping_path)
    raw = json.loads(json.loads((project / "acceptance-review.json").read_text())["raw_results"][0])
    raw["reviewed_section_ids"] = [section.section_id for section in prepared.sections]
    assert ingest_mapping_review(prepared, [json.dumps(raw)], review_path).ready
    (project / "mapping.json").unlink()
    (project / "acceptance-review.json").unlink()
    path = run(project, mapping=mapping_path.relative_to(project).as_posix())
    assert verify_execution_receipt(path, project, FEATURE).valid
    return path, mapping_path, review_path


@pytest.mark.parametrize("changed", ["mapping", "review"])
def test_governed_mapping_and_raw_review_cannot_change_inside_generated_cache(
    project: Path, changed: str
) -> None:
    path, mapping_path, review_path = _capture_cached_mapping(project)
    # Even a semantically identical JSON rewrite changes governed raw evidence.
    target = mapping_path if changed == "mapping" else review_path
    target.write_text(target.read_text() + "\n")
    result = verify_execution_receipt(path, project, FEATURE)
    assert not result.valid
    assert any("Governed acceptance input changed" in gap for gap in result.gaps)


def test_partial_mapping_reviews_full_context_but_certifies_only_declared_ac(project: Path) -> None:
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        spec.read_text() + "\n## Other contract\nFR-002: Keep history.\n"
        "AC-002: History persists.\nSC-001: All selected behavior is proven.\n"
    )
    mapping_path = project / "mapping.json"
    prepared = prepare_mapping_review(project, FEATURE, mapping_path)
    assert prepared.requirement_scope == (AC,)
    assert [item.requirement_id for item in prepared.requirements] == [AC]
    assert any("AC-002: History persists." in section.text for section in prepared.sections)
    review_path = project / "acceptance-review.json"
    raw = json.loads(json.loads(review_path.read_text())["raw_results"][0])
    raw["reviewed_section_ids"] = [section.section_id for section in prepared.sections]
    source = next(
        section
        for section in prepared.sections
        if section.role == "spec" and "AC-001" in section.text
    )
    raw["conclusions"][0]["source_citations"][0]["section_id"] = source.section_id
    assert ingest_mapping_review(prepared, [json.dumps(raw)], review_path).ready
    path = run(project)
    result = verify_execution_receipt(path, project, FEATURE)
    assert result.valid and result.certified_acs == [AC]
    assert not verify_execution_receipt(path, project, FEATURE, (AC, f"{FEATURE}:AC-002")).valid
    spec.write_text(spec.read_text().replace("History persists.", "History is deleted."))
    changed = prepare_mapping_review(project, FEATURE, mapping_path)
    assert changed.context_hash != prepared.context_hash
    assert not verify_execution_receipt(path, project, FEATURE).valid


@pytest.mark.parametrize("scope", [(), ("f:AC-999",), ("f:AC-001", "f:AC-001")])
def test_explicit_review_scope_rejects_empty_foreign_or_duplicate_ids(
    scope: tuple[str, ...],
) -> None:
    from validator.semantic.review_context import prepare_review_context

    result = prepare_review_context(
        "f",
        {"spec": "AC-001: Add.", "plan": "assert add()==3"},
        model="reviewer/v1",
        requirement_scope=scope,
    )
    assert not result.complete
    assert result.errors


def test_global_review_default_identity_stays_unchanged_by_optional_scope() -> None:
    from validator.semantic.review_context import prepare_review_context

    result = prepare_review_context(
        "scope-hash-control",
        {"spec": "AC-001: Add one and two.", "plan": "assert add(1,2)==3"},
        model="reviewer/v1",
    )
    assert result.context_hash == "1f4e31b94184ef1425e5a3753bd32b050759fd6f96f59b1611c68dea422e3e1a"
    assert result.requirement_scope is None


def test_scoped_mapping_review_retains_actual_blocking_findings(project: Path) -> None:
    prepared = prepare_mapping_review(project, FEATURE, project / "mapping.json")
    review_path = project / "acceptance-review.json"
    raw = json.loads(json.loads(review_path.read_text())["raw_results"][0])
    raw["findings"] = [
        {
            "category": "coverage",
            "severity": "blocking",
            "description": "Selected outcome lacks sufficient checks.",
            "suggestion": "Add the missing selected outcome assertion.",
            "citations": raw["conclusions"][0]["source_citations"],
        }
    ]
    receipt = ingest_mapping_review(prepared, [json.dumps(raw)], review_path)
    assert receipt.complete and not receipt.ready
    assert not verify_execution_receipt(run(project), project, FEATURE).valid


@pytest.mark.parametrize("changed", ["mapping", "review"])
@pytest.mark.parametrize("restore", [False, True])
def test_governed_inputs_changed_during_certification_cannot_pass(
    project: Path, monkeypatch: pytest.MonkeyPatch, changed: str, restore: bool
) -> None:
    from validator import execution_evidence

    path, mapping_path, review_path = _capture_cached_mapping(project)
    target = mapping_path if changed == "mapping" else review_path
    original = target.read_bytes()
    certify = execution_evidence.certify_mappings

    def swap(*args, **kwargs):
        target.write_bytes(original + b"\n")
        try:
            return certify(*args, **kwargs)
        finally:
            if restore:
                target.write_bytes(original)

    monkeypatch.setattr(execution_evidence, "certify_mappings", swap)
    result = verify_execution_receipt(path, project, FEATURE)
    assert not result.valid and result.certified_acs == []
    assert any("Governed acceptance input changed" in gap for gap in result.gaps)


def test_governed_review_changed_after_certification_cannot_pass(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator import execution_evidence

    path, _, review_path = _capture_cached_mapping(project)
    certify = execution_evidence.certify_mappings

    def swap(*args, **kwargs):
        result = certify(*args, **kwargs)
        assert result == ([AC], [])
        review_path.write_bytes(review_path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(execution_evidence, "certify_mappings", swap)
    result = verify_execution_receipt(path, project, FEATURE)
    assert not result.valid and result.certified_acs == []
    assert any("Governed acceptance input changed" in gap for gap in result.gaps)


def test_declared_review_acceptance_cannot_be_certified_by_passing_pytest(project: Path) -> None:
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        spec.read_text() + "\n**Evidence:** review\n**Review inputs:** [Code](../../../app.py)\n"
    )
    with pytest.raises(ValueError, match="declared execution evidence"):
        prepare_mapping_review(project, FEATURE, project / "mapping.json")
    result = verify_execution_receipt(run(project), project, FEATURE, (AC,))
    assert result.executed_tests[0].status == "passed"
    assert not result.valid and result.certified_acs == []
    assert "Required acceptance does not declare execution evidence" in result.gaps


def test_execution_mapping_certifies_only_its_declared_kind_with_review_ac_present(project: Path):
    from tests.execution_evidence_support import _review_response

    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        spec.read_text() + "\n**Evidence:** execution\n\n## AC-002\nReview the migration.\n"
        "**Evidence:** review\n**Review inputs:** [Code](../../../app.py)\n"
    )
    prepared = prepare_mapping_review(project, FEATURE, project / "mapping.json")
    assert prepared.requirement_scope == (AC,)
    receipt = project / "acceptance-review.json"
    assert ingest_mapping_review(prepared, [_review_response(prepared)], receipt).ready
    path = run(project)
    result = verify_execution_receipt(path, project, FEATURE, (AC,))
    assert result.valid and result.certified_acs == [AC]
    missing = verify_execution_receipt(path, project, FEATURE, (AC, f"{FEATURE}:AC-002"))
    assert not missing.valid and missing.certified_acs == []
    assert "Required acceptance does not declare execution evidence" in missing.gaps


def test_transient_spec_replacement_cannot_borrow_an_old_execution_review(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator import execution_mapping

    spec = project / ".specs/features" / FEATURE / "spec.md"
    old = spec.read_bytes()
    declared_review = old + b"\n**Evidence:** review\n**Review inputs:** [Code](../../../app.py)\n"
    spec.write_bytes(declared_review)
    path = run(project)
    read = execution_mapping.read_regular

    def swapped_read(target, root):
        if target == spec:
            spec.write_bytes(old)
            try:
                return read(target, root)
            finally:
                spec.write_bytes(declared_review)
        return read(target, root)

    monkeypatch.setattr(execution_mapping, "read_regular", swapped_read)
    result = verify_execution_receipt(path, project, FEATURE)
    assert spec.read_bytes() == declared_review
    assert not result.valid and result.certified_acs == []
    assert "Consumed acceptance source differs from captured execution inputs" in result.gaps


def test_policy1_keeps_original_scope_but_current_policy_requires_real_declarations(project: Path):
    from tests.execution_evidence_support import _review_response
    from validator.execution_mapping import AcceptanceMapping, _prepare_mapping_review

    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(spec.read_text().replace("# Addition", "## Historical contract"))
    mapping_path = project / "mapping.json"
    mapping = AcceptanceMapping.model_validate_json(mapping_path.read_bytes())
    prepared = _prepare_mapping_review(project, FEATURE, mapping_path, mapping, evidence_policy="1")
    assert ingest_mapping_review(
        prepared, [_review_response(prepared)], project / "acceptance-review.json"
    ).ready
    path = run(project)
    legacy = verify_execution_receipt(path, project, FEATURE, (AC,), evidence_policy="1")
    assert legacy.valid and legacy.certified_acs == [AC]
    current = verify_execution_receipt(path, project, FEATURE, (AC,))
    assert not current.valid and current.certified_acs == []

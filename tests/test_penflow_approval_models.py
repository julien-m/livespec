"""C51 data-shape tests, independently checked against the producer schema."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from validator.penflow_approval_models import (
    ApprovalInputs,
    ApprovedBinding,
    ApprovedSource,
    Assertion,
    AuthorityImport,
    Change,
    ExpectedOutcome,
    File,
    ImportedAuthorityFile,
    PolicySource,
    Projection,
    Requirement,
    RequirementsBaseline,
    ReviewApproval,
    ReviewResult,
    ReviewSnapshot,
    Scope,
    StrictModel,
    VerificationPolicy,
)

# @spec AC-008: Strict reviewed source types
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-008


@pytest.fixture
def examples() -> dict[str, dict[str, Any]]:
    """Nontrivial nested fixture shared by the independent shape checks."""
    file = {"path": "spec.md", "sha256": "a" * 64}
    scope = {"project_root": "/project", "workspace": "/project/penflow"}
    assertion = {
        "operator": "greater_than",
        "pointer": "/count",
        "capability": "ui",
        "expected": {"mixed": [True, 1, 1.5, None, "1", {"x": False}]},
    }
    expected = {
        "obligation_id": "save",
        "source_pointer": "FR-001",
        "category": "result",
        "assertions": [assertion],
    }
    binding = {
        "requirement_id": "FR-001",
        "obligation_id": "save",
        "category": "result",
        "expected": expected,
    }
    requirement = {"id": "FR-001", "source_pointer": "spec.md#fr-001", "text_sha256": "b" * 64}
    projection = {
        "source_kind": "livespec-fr-ac-v1",
        "sources": [file],
        "requirements": [requirement],
        "bindings": [binding],
        "uncovered": [],
    }
    source = {**file, "semantic_sha256": "c" * 64, "reviewed_snapshot": file}
    inputs = {
        "sources": [source],
        "plans": [source],
        "contract": file,
        "projection_sha256": "d" * 64,
        "selection_sha256": "e" * 64,
    }
    change = {
        "source_path": "spec.md",
        "old_sha256": "f" * 64,
        "new_sha256": "a" * 64,
        "removed_requirement_ids": [],
        "changed_binding_ids": ["save"],
    }
    shared = {
        "version": 1,
        "disposition": "active",
        "command": "spec-plan",
        "feature": "077-example",
        "scope": scope,
        "selection": ["077-example"],
        "retired_features": [],
        "inputs": inputs,
        "prior_receipt": None,
        "changes": [change],
    }
    review = {
        "invocation_id": "review-1",
        "producer_id": "reviewer",
        "input_sha256": "a" * 64,
        "output": file,
        "verdict": "PASS",
        "blocking_count": 0,
        "findings": [{"severity": "INFO", "message": "Checked", "requirement_ids": []}],
    }
    policy = {
        "version": 1,
        "generated_docs": "required",
        "native_geometry": "not_applicable",
        "homologous_references": "required",
        "native_export": "not_applicable",
    }
    return {
        "verification-policy": policy,
        "verification-policy-source": {
            "kind": "penflow-verification-policy-source",
            "version": 1,
            "workflow": file,
            "decisions": policy,
            "inherited_authority": None,
        },
        "brainstorm-authority-import": {
            "kind": "penflow-brainstorm-authority-import",
            "version": 1,
            "origin_scope": scope,
            "workspace": "penflow",
            "report": file,
            "files": [{"source_path": "/former/project/spec.md", **file}],
        },
        "file": file,
        "scope": scope,
        "assertion": assertion,
        "expected-outcome": expected,
        "approved-binding": binding,
        "requirement": requirement,
        "projection": projection,
        "approved-source": source,
        "approval-inputs": inputs,
        "review-snapshot": {
            **shared,
            "kind": "livespec-penflow-review-snapshot",
            "projection": projection,
        },
        "review-result": {
            "kind": "livespec-penflow-review-result",
            "version": 1,
            "snapshot": file,
            "review": review,
        },
        "review-approval": {
            **shared,
            "kind": "livespec-penflow-review-approval",
            "review": review,
            "snapshot": file,
        },
        "requirements-baseline": {
            "kind": "livespec-penflow-requirements-baseline",
            "version": 1,
            "disposition": "active",
            "scope": scope,
            "selection": ["077-example"],
            "retired_features": [],
            "approval_receipts": [file],
            "sources": [source],
            "contract": file,
            "projection": projection,
            "previous": None,
        },
    }


MODELS: dict[str, type[StrictModel]] = {
    "verification-policy": VerificationPolicy,
    "verification-policy-source": PolicySource,
    "brainstorm-authority-import": AuthorityImport,
    "file": File,
    "scope": Scope,
    "assertion": Assertion,
    "expected-outcome": ExpectedOutcome,
    "approved-binding": ApprovedBinding,
    "requirement": Requirement,
    "projection": Projection,
    "approved-source": ApprovedSource,
    "approval-inputs": ApprovalInputs,
    "review-snapshot": ReviewSnapshot,
    "review-result": ReviewResult,
    "review-approval": ReviewApproval,
    "requirements-baseline": RequirementsBaseline,
}


@pytest.mark.parametrize("name", MODELS)
def test_roundtrip_preserves_exact_public_data(
    name: str, examples: dict[str, dict[str, Any]]
) -> None:
    payload = examples[name]
    parsed = MODELS[name].model_validate(payload)
    assert parsed.model_dump(mode="json") == payload
    assert json.loads(parsed.model_dump_json()) == payload


@pytest.mark.parametrize("name", MODELS)
def test_public_schema_accepts_serialized_models(
    name: str, examples: dict[str, dict[str, Any]]
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = (
        Path(__file__).resolve().parents[2] / "penflow/.specs/features/"
        "077-complete-verification-workflow/contracts/c51-contracts.schema.json"
    )
    if not schema_path.exists():
        pytest.skip("Producer checkout unavailable; local strict model tests still run")
    schema = json.loads(schema_path.read_text())
    schema["$ref"] = f"#/$defs/{name}"
    jsonschema.Draft202012Validator(schema).validate(
        MODELS[name].model_validate(examples[name]).model_dump(mode="json")
    )


@pytest.mark.parametrize("name", MODELS)
def test_reject_missing_and_extra_fields(name: str, examples: dict[str, dict[str, Any]]) -> None:
    for field in examples[name]:
        payload = copy.deepcopy(examples[name])
        del payload[field]
        with pytest.raises(ValidationError):
            MODELS[name].model_validate(payload)
    with pytest.raises(ValidationError):
        MODELS[name].model_validate({**examples[name], "unexpected": True})


@pytest.mark.parametrize(
    "name",
    [
        "review-snapshot",
        "review-result",
        "review-approval",
        "requirements-baseline",
        "verification-policy",
        "verification-policy-source",
        "brainstorm-authority-import",
    ],
)
@pytest.mark.parametrize("version", [True, False, "1", 1.0, 2, None])
def test_reject_non_integer_or_unknown_versions(
    name: str, version: object, examples: dict[str, dict[str, Any]]
) -> None:
    with pytest.raises(ValidationError):
        MODELS[name].model_validate({**examples[name], "version": version})


@pytest.mark.parametrize("value", [True, False, "0", -1, 0.0])
def test_nested_review_count_is_strict(value: object, examples: dict[str, dict[str, Any]]) -> None:
    for name in ["review-result", "review-approval"]:
        payload = copy.deepcopy(examples[name])
        payload["review"]["blocking_count"] = value
        with pytest.raises(ValidationError):
            MODELS[name].model_validate(payload)


@pytest.mark.parametrize("sha", ["a" * 63, "a" * 65, "A" * 64, "g" * 64, 1])
def test_sha256_must_match_public_lowercase_digest(sha: object) -> None:
    with pytest.raises(ValidationError):
        File.model_validate({"path": "file", "sha256": sha})


def test_nested_json_values_keep_python_types(examples: dict[str, dict[str, Any]]) -> None:
    parsed = Assertion.model_validate(examples["assertion"])
    values = parsed.model_dump(mode="json")["expected"]["mixed"]
    assert [type(value) for value in values] == [bool, int, float, type(None), str, dict]
    for value in [b"bytes", (1, 2), {1: "integer key"}, float("nan"), float("inf")]:
        with pytest.raises(ValidationError):
            Assertion.model_validate({**examples["assertion"], "expected": value})


def test_empty_lists_categories_and_pointers_follow_schema(
    examples: dict[str, dict[str, Any]],
) -> None:
    for name, field in [
        ("projection", "sources"),
        ("projection", "requirements"),
        ("approval-inputs", "sources"),
        ("expected-outcome", "assertions"),
        ("review-snapshot", "selection"),
        ("requirements-baseline", "approval_receipts"),
        ("requirements-baseline", "sources"),
    ]:
        with pytest.raises(ValidationError):
            MODELS[name].model_validate({**examples[name], field: []})
    for name in ["approved-binding", "expected-outcome"]:
        with pytest.raises(ValidationError):
            MODELS[name].model_validate({**examples[name], "category": "unknown"})
    with pytest.raises(ValidationError):
        Assertion.model_validate({**examples["assertion"], "pointer": "not-a-pointer"})
    with pytest.raises(ValidationError):
        Requirement.model_validate({**examples["requirement"], "category": "result"})
    with pytest.raises(ValidationError):
        File.model_validate({"path": "", "sha256": "a" * 64})


def test_change_rejects_unknown_fields_and_empty_identifiers(
    examples: dict[str, dict[str, Any]],
) -> None:
    payload = examples["review-snapshot"]["changes"][0]
    assert Change.model_validate(payload).model_dump(mode="json") == payload
    for invalid in [{**payload, "extra": 1}, {**payload, "removed_requirement_ids": [""]}]:
        with pytest.raises(ValidationError):
            Change.model_validate(invalid)


@pytest.mark.parametrize("name", ["review-snapshot", "review-approval", "requirements-baseline"])
def test_disposition_is_required_strict_and_allows_retirement(
    name: str, examples: dict[str, dict[str, Any]]
) -> None:
    payload = _retired(examples[name])
    retired = MODELS[name].model_validate(payload)
    assert retired.model_dump(mode="json")["disposition"] == "retired"
    for invalid in ["unknown", "", True, None, 1]:
        with pytest.raises(ValidationError):
            MODELS[name].model_validate({**examples[name], "disposition": invalid})
    without_disposition = {
        key: value for key, value in examples[name].items() if key != "disposition"
    }
    with pytest.raises(ValidationError):
        MODELS[name].model_validate(without_disposition)


def _retired(payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    value.update(disposition="retired", retired_features=value["selection"])
    if "projection" in value:
        value["projection"] = {
            "source_kind": "livespec-fr-ac-v1",
            "sources": [],
            "requirements": [],
            "bindings": [],
            "uncovered": [],
        }
    return value


@pytest.mark.parametrize("name", ["review-snapshot", "review-approval", "requirements-baseline"])
def test_cumulative_selection_constraints(name: str, examples: dict[str, dict[str, Any]]) -> None:
    payload = {
        **examples[name],
        "selection": ["077-example", "078-example"],
        "retired_features": ["077-example"],
    }
    assert MODELS[name].model_validate(payload).model_dump(mode="json")["disposition"] == "active"
    for mutation in [
        {"retired_features": ["999-foreign"]},
        {"retired_features": ["077-example", "077-example"]},
        {"selection": ["078-example", "077-example"]},
        {"selection": ["077-example", "077-example"]},
        {"retired_features": ["077-example", "078-example"]},
        {"disposition": "retired"},
    ]:
        with pytest.raises(ValidationError):
            MODELS[name].model_validate({**payload, **mutation})


@pytest.mark.parametrize("name", ["review-snapshot", "requirements-baseline"])
def test_empty_projection_is_valid_only_in_fully_retired_envelope(
    name: str, examples: dict[str, dict[str, Any]]
) -> None:
    retired = _retired(examples[name])
    assert MODELS[name].model_validate(retired).model_dump(mode="json") == retired
    with pytest.raises(ValidationError):
        MODELS[name].model_validate({**examples[name], "projection": retired["projection"]})
    with pytest.raises(ValidationError):
        MODELS[name].model_validate({**retired, "projection": examples[name]["projection"]})
    with pytest.raises(ValidationError):
        Projection.model_validate(retired["projection"])


@pytest.mark.parametrize("name", ["review-snapshot", "review-approval", "requirements-baseline"])
def test_public_schema_accepts_retired_envelopes(
    name: str, examples: dict[str, dict[str, Any]]
) -> None:
    examples[name] = _retired(examples[name])
    test_public_schema_accepts_serialized_models(name, examples)


def test_approval_inputs_require_nonempty_plans_and_reject_legacy_plan(
    examples: dict[str, dict[str, Any]],
) -> None:
    value = examples["approval-inputs"]
    with pytest.raises(ValidationError):
        ApprovalInputs.model_validate({**value, "plans": []})
    with pytest.raises(ValidationError):
        ApprovalInputs.model_validate({**value, "plan": value["plans"][0]})


def test_optional_policy_preserves_historical_omission_and_required_nulls(
    examples: dict[str, dict[str, Any]],
) -> None:
    for name in ["review-snapshot", "review-approval"]:
        historical = MODELS[name].model_validate(examples[name])
        assert historical.model_dump(mode="json") == examples[name]
        assert json.loads(historical.model_dump_json())["prior_receipt"] is None
        current = copy.deepcopy(examples[name])
        current["inputs"]["verification_policy"] = examples["file"]
        assert MODELS[name].model_validate(current).model_dump(mode="json") == current
    for malformed in [None, {}, True, "policy.json"]:
        with pytest.raises(ValidationError):
            ApprovalInputs.model_validate(
                {**examples["approval-inputs"], "verification_policy": malformed}
            )


@pytest.mark.parametrize("name", ["approval-inputs", "review-snapshot", "review-approval"])
def test_public_schema_accepts_explicit_verification_policy_reference(
    name: str, examples: dict[str, dict[str, Any]]
) -> None:
    target = examples[name] if name == "approval-inputs" else examples[name]["inputs"]
    target["verification_policy"] = examples["file"]
    test_public_schema_accepts_serialized_models(name, examples)


@pytest.mark.parametrize("decision", [True, False, 1, None, "optional", "PASS"])
def test_policy_decisions_reject_coercion_and_unknown_values(
    decision: object, examples: dict[str, dict[str, Any]]
) -> None:
    for name in ["generated_docs", "native_geometry", "homologous_references", "native_export"]:
        with pytest.raises(ValidationError):
            VerificationPolicy.model_validate({**examples["verification-policy"], name: decision})


# @spec AC-009: Imported authority keeps a closed typed boundary
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-009
def test_import_references_are_closed_nonempty_shapes(examples: dict[str, dict[str, Any]]) -> None:
    imported = examples["brainstorm-authority-import"]
    for mutation in [{"files": []}, {"workspace": ""}, {"report": None}]:
        with pytest.raises(ValidationError):
            AuthorityImport.model_validate({**imported, **mutation})
    reference = imported["files"][0]
    for field in ["source_path", "path", "sha256"]:
        for value in ["", 1, None]:
            with pytest.raises(ValidationError):
                ImportedAuthorityFile.model_validate({**reference, field: value})
    with pytest.raises(ValidationError):
        ImportedAuthorityFile.model_validate({**reference, "unexpected": True})


def test_policy_source_cannot_infer_missing_ancestry_or_workflow(
    examples: dict[str, dict[str, Any]],
) -> None:
    value = examples["verification-policy-source"]
    for field in ["workflow", "inherited_authority"]:
        with pytest.raises(ValidationError):
            PolicySource.model_validate({key: item for key, item in value.items() if key != field})
    with pytest.raises(ValidationError):
        PolicySource.model_validate({**value, "workflow": None})

"""Bind acceptance results to exact assertions and independently grounded review."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .acceptance_requirements import execution_acceptance_ids
from .execution_reports import ExecutedAssertion, ExecutedTest, junit_test_id
from .execution_scope import digest, read_regular
from .normative_identity import normative_hash
from .semantic.review_context import DEFAULT_MAX_CHARS, PreparedReview, prepare_review_context
from .semantic.review_contract import ReviewReceipt, validate_review_result
from .semantic.review_receipts import save_review_receipt, verify_review_receipt


class AcceptanceBinding(BaseModel):
    """Generated mapping, untrusted until exact source and raw review are checked."""

    model_config = ConfigDict(extra="forbid", strict=True)
    requirement_id: str
    test_id: str
    expected: str = Field(min_length=1)
    assertion_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    source_sha256: str
    justification: str = Field(min_length=1)


class AcceptanceMapping(BaseModel):
    """One feature's assertions and the actual independent review receipt."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str = "1"
    feature: str
    reviewer_model: str = Field(min_length=1)
    review_max_chars: int = Field(default=DEFAULT_MAX_CHARS, ge=1000, le=200000)
    review_receipt_path: str
    bindings: list[AcceptanceBinding] = Field(min_length=1)


def _load_mapping(project_root: Path, mapping_path: Path) -> AcceptanceMapping:
    return AcceptanceMapping.model_validate_json(read_regular(mapping_path, project_root))


def prepare_mapping_review(project_root: Path, feature: str, mapping_path: Path) -> PreparedReview:
    """Prepare complete spec, exact test files and mapping for the existing test reviewer."""
    mapping = _load_mapping(project_root, mapping_path)
    return _prepare_mapping_review(project_root, feature, mapping_path, mapping)


def _prepare_mapping_review(
    project_root: Path,
    feature: str,
    mapping_path: Path,
    mapping: AcceptanceMapping,
    *,
    evidence_policy: Literal["1", "2"] = "2",
) -> PreparedReview:
    """Prepare from the same parsed mapping consumed by certification."""
    if mapping.schema_version != "1" or mapping.feature != feature:
        raise ValueError("Foreign or unsupported acceptance mapping")
    scope = tuple(sorted({binding.requirement_id for binding in mapping.bindings}))
    if any(not re.fullmatch(re.escape(feature) + r":AC-\d+", item) for item in scope):
        raise ValueError("Acceptance mapping scope requires qualified feature AC identities")
    spec = f".specs/features/{feature}/spec.md"
    sources = {spec: read_regular(project_root / spec, project_root).decode()}
    if evidence_policy == "2" and set(scope) - set(
        execution_acceptance_ids(project_root, feature, spec_text=sources[spec])
    ):
        raise ValueError("Acceptance mappings require declared execution evidence")
    roles = {spec: "spec"}
    for binding in mapping.bindings:
        source = read_regular(project_root / binding.assertion_path, project_root)
        if digest(source) != binding.source_sha256:
            raise ValueError(f"Assertion source changed: {binding.assertion_path}")
        _assertion_span(binding, source.decode())
        sources[binding.assertion_path] = source.decode()
        roles[binding.assertion_path] = "plan"
    key = mapping_path.relative_to(project_root).as_posix()
    sources[key] = mapping.model_dump_json()
    roles[key] = "plan"
    return prepare_review_context(
        feature,
        sources,
        kind="plan",
        model=mapping.reviewer_model,
        source_roles=roles,
        max_chars=mapping.review_max_chars,
        requirement_scope=scope,
    )


def ingest_mapping_review(
    prepared: PreparedReview,
    raw_results: list[str],
    receipt_path: Path,
    synthesis: str | None = None,
) -> ReviewReceipt:
    """Validate actual reviewer responses and persist the result, including failure gaps."""
    from .mapping_review_validation import mapping_review_errors

    receipt = validate_review_result(prepared, raw_results, synthesis)
    if receipt.ready and (errors := mapping_review_errors(prepared, receipt)):
        receipt = receipt.model_copy(
            update={"complete": False, "ready": False, "errors": [*receipt.errors, *errors]}
        )
    save_review_receipt(receipt_path, receipt)
    return receipt


def _assertion_span(binding: AcceptanceBinding, text: str) -> str:
    lines = text.splitlines(keepends=True)
    if binding.end_line < binding.start_line or binding.end_line > len(lines):
        raise ValueError("Invalid assertion span")
    if binding.assertion_path.endswith(".py"):
        tree = ast.parse(text)
        test_name = binding.test_id.rsplit("::", 1)[-1].split("[", 1)[0]
        matches = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == test_name
            and node.lineno <= binding.start_line
            and (node.end_lineno or node.lineno) >= binding.end_line
        ]
        selected = [
            node
            for function in matches
            for node in ast.walk(function)
            if isinstance(node, ast.Assert)
            and binding.start_line <= node.lineno <= binding.end_line
        ]
        if len(selected) != 1:
            raise ValueError("Binding does not cite an assertion inside the executed Python test")
    return "".join(lines[binding.start_line - 1 : binding.end_line]).strip()


def _matches_expression(observed: ExecutedAssertion, source: str) -> bool:
    nodes = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assert) and node.lineno == observed.line
    ]
    if len(nodes) != 1:
        return False
    try:
        actual = ast.parse(observed.assertion, mode="eval").body
    except SyntaxError:
        return False
    return ast.dump(nodes[0].test) == ast.dump(actual)


def _observed_assertion(
    binding: AcceptanceBinding, assertions: list[ExecutedAssertion], project_root: Path, source: str
) -> bool:
    """Match the actual assertion callback to the exact reviewed source expression."""
    return any(
        assertion.status == "passed"
        and binding.test_id in (assertion.test_id, junit_test_id(assertion.test_id))
        and Path(assertion.path) == project_root / binding.assertion_path
        and binding.start_line <= assertion.line <= binding.end_line
        and _matches_expression(assertion, source)
        for assertion in assertions
    )


def _mapping_inputs(
    project_root: Path,
    mapping_path: Path,
    expected_inputs: dict[str, str] | None,
) -> tuple[AcceptanceMapping, bytes, bool]:
    """Read and check the exact governed bytes subsequently consumed by certification."""
    mapping_bytes = read_regular(mapping_path, project_root)
    mapping = AcceptanceMapping.model_validate_json(mapping_bytes)
    raw = read_regular(project_root / mapping.review_receipt_path, project_root)
    if expected_inputs is not None and any(
        expected_inputs.get(key) != digest(value)
        for key, value in (
            (mapping_path.relative_to(project_root).as_posix(), mapping_bytes),
            (mapping.review_receipt_path, raw),
        )
    ):
        return mapping, raw, False
    return mapping, raw, True


def certify_mappings(
    project_root: Path,
    feature: str,
    mapping_path: Path,
    tests: list[ExecutedTest],
    assertions: list[ExecutedAssertion],
    *,
    expected_inputs: dict[str, str] | None = None,
    expected_sources: dict[str, str] | None = None,
    evidence_policy: Literal["1", "2"] = "2",
) -> tuple[list[str], list[str]]:
    """Revalidate raw independent review and passing assertion bindings, never names alone."""
    mapping, raw, current = _mapping_inputs(project_root, mapping_path, expected_inputs)
    if not current:
        return [], ["Governed acceptance input changed while being consumed"]
    prepared = _prepare_mapping_review(
        project_root, feature, mapping_path, mapping, evidence_policy=evidence_policy
    )
    if expected_sources is not None and not _prepared_sources_match(
        prepared, expected_sources, mapping_path.relative_to(project_root).as_posix()
    ):
        return [], ["Consumed acceptance source differs from captured execution inputs"]
    receipt = ReviewReceipt.model_validate_json(raw)
    rebuilt = validate_review_result(prepared, receipt.raw_results, receipt.synthesis)
    if not prepared.cacheable or not rebuilt.ready or not verify_review_receipt(receipt, prepared):
        return [], ["Independent acceptance review is missing, stale, incomplete or altered"]
    return _certified_bindings(mapping, prepared, rebuilt, project_root, tests, assertions)


def _source_texts(prepared: PreparedReview) -> dict[str, str]:
    """Reconstruct exact frozen source bytes for every subsequent assertion check."""
    sources: dict[str, str] = {}
    for section in prepared.sections:
        sources[section.source] = sources.get(section.source, "") + section.text
    return sources


def _prepared_sources_match(
    prepared: PreparedReview, expected: dict[str, str], mapping_path: str
) -> bool:
    """Compare the exact consumed spec/test bytes, permitting only selected lifecycle values."""
    spec = f".specs/features/{prepared.feature}/spec.md"
    text = _source_texts(prepared)[spec]
    for name, raw_hash in prepared.source_hashes.items():
        if name == spec:
            actual = normative_hash(text, lifecycle_document=True)
        elif name == mapping_path:
            continue  # Mapping JSON has its separate exact consumed-input check.
        else:
            actual = raw_hash
        if expected.get(name) != actual:
            return False
    return True


def _certified_bindings(
    mapping: AcceptanceMapping,
    prepared: PreparedReview,
    rebuilt: ReviewReceipt,
    project_root: Path,
    tests: list[ExecutedTest],
    assertions: list[ExecutedAssertion],
) -> tuple[list[str], list[str]]:
    """Certify only independently grounded assertions actually observed passing."""
    sources = _source_texts(prepared)
    passing = {test.test_id for test in tests if test.status == "passed"}
    conclusions = {item.requirement_id: item for item in rebuilt.conclusions}
    sections = {item.section_id: item for item in prepared.sections}
    certified: list[str] = []
    gaps: list[str] = []
    for binding in mapping.bindings:
        conclusion = conclusions.get(binding.requirement_id)
        span = _assertion_span(binding, sources[binding.assertion_path])
        grounded = bool(
            conclusion
            and conclusion.disposition == "covered"
            and any(
                sections[citation.section_id].source == binding.assertion_path
                and span in citation.excerpt
                for citation in conclusion.plan_citations
            )
        )
        observed = _observed_assertion(
            binding, assertions, project_root, sources[binding.assertion_path]
        )
        if (
            not observed
            or binding.test_id not in passing
            or not grounded
            or not binding.requirement_id.startswith(f"{prepared.feature}:AC-")
        ):
            gaps.append(
                f"Unproven acceptance binding: {binding.requirement_id} / {binding.test_id}"
            )
        else:
            certified.append(binding.requirement_id)
    return sorted(set(certified)), gaps

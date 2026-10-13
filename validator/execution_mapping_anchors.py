"""Derived acceptance mappings and their certification without review (feature 087)."""

from __future__ import annotations

from pathlib import Path

from .acceptance_anchors import Derivation, derive_acceptance
from .execution_mapping import (
    AcceptanceBinding,
    AcceptanceMapping,
    _assertion_span,  # pyright: ignore[reportPrivateUsage]
    _observed_assertion,  # pyright: ignore[reportPrivateUsage]
)
from .execution_reports import ExecutedAssertion, ExecutedTest, resolve_test_id
from .execution_scope import digest, read_regular
from .normative_identity import normative_hash


def derived_mapping(
    project_root: Path, feature: str
) -> tuple[AcceptanceMapping | None, Derivation]:
    """Derive the mapping from `@spec` anchors; None when no binding or a blocking issue."""
    derivation = derive_acceptance(project_root, feature)
    if derivation.blocking or not derivation.bindings:
        return None, derivation
    bindings = [AcceptanceBinding(**vars(item)) for item in derivation.bindings]
    return AcceptanceMapping(feature=feature, bindings=bindings, derivation="anchors"), derivation


def certify_anchored(
    project_root: Path,
    feature: str,
    mapping: AcceptanceMapping,
    tests: list[ExecutedTest],
    assertions: list[ExecutedAssertion],
    expected_sources: dict[str, str] | None,
) -> tuple[list[str], list[str]]:
    """Re-derive the anchors and certify only the same bindings observed passing."""
    # @spec FR-005: Certify anchored bindings without review grounding
    #   — .specs/features/087-anchor-derived-acceptance/spec.md#fr-005
    if mapping.feature != feature:
        return [], ["Foreign acceptance mapping"]
    current, derivation = derived_mapping(project_root, feature)
    if current is None:
        codes = ", ".join(sorted({issue.code for issue in derivation.blocking})) or "no_binding"
        return [], [f"Acceptance anchors do not derive a mapping: {codes}"]
    if current.bindings != mapping.bindings:
        return [], ["Anchored acceptance mapping differs from the current test anchors"]
    spec = f".specs/features/{feature}/spec.md"
    sources = {spec: read_regular(project_root / spec, project_root)}
    for binding in mapping.bindings:
        sources[binding.assertion_path] = read_regular(
            project_root / binding.assertion_path, project_root
        )
    if expected_sources is not None and any(
        expected_sources.get(name)
        != (
            normative_hash(data.decode(), lifecycle_document=True) if name == spec else digest(data)
        )
        for name, data in sources.items()
    ):
        return [], ["Consumed acceptance source differs from captured execution inputs"]
    passing = {test.test_id for test in tests if test.status == "passed"}
    certified: list[str] = []
    gaps: list[str] = []
    for binding in mapping.bindings:
        text = sources[binding.assertion_path].decode()
        test_id = resolve_test_id(binding.test_id, tests)
        if (
            digest(sources[binding.assertion_path]) == binding.source_sha256
            and _assertion_span(binding, text)
            and test_id in passing
            and _observed_assertion(binding, test_id, assertions, project_root, text)
        ):
            certified.append(binding.requirement_id)
        else:
            gaps.append(
                f"Unproven acceptance binding: {binding.requirement_id} / {binding.test_id}"
            )
    return sorted(set(certified)), gaps

"""Typed contracts for ARS source decision manifests."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

SourceDecisionKind = Literal[
    "executable",
    "generated-executable",
    "advisory",
    "non-executable",
    "unsupported",
    "excluded",
]


class RuleDecision(TypedDict):
    decision_id: str
    decision_kind: SourceDecisionKind
    kind: SourceDecisionKind
    reason: str
    decision_anchor: str
    source_path: str
    source_hash: str
    source_anchor_policy: str
    source_anchor: str
    domain: str
    language: str
    missing_capability: str
    future_backend_candidate: str
    review_guidance: str
    manual_review_surface: str
    rule_ids: list[str]
    backend_ids: list[str]
    detector_ids: list[str]
    fixture_families: list[str]
    test_ids: list[str]
    deterministic_test_evidence: list[dict[str, str]]
    non_blocking: bool
    non_blocking_behavior: str
    generator_id: str
    generator_version: str
    input_source_hashes: list[str]
    generated_catalog_snapshot: str
    catalog_errors: NotRequired[list[str]]


class SourceDecision(TypedDict):
    source_id: str
    source_path: str
    source_hash: str
    source_anchor_policy: str
    source_anchor: str
    domains: list[str]
    languages: list[str]
    classification: dict[str, str]
    rule_decision: RuleDecision


class ExcludedDecision(TypedDict):
    source_id: str
    source_path: str
    source_hash: str
    rule_decision: RuleDecision


class RuleDecisionManifest(TypedDict):
    total_source_count: int
    decided_source_count: int
    undecided_source_count: int
    executable_source_count: int
    generated_executable_source_count: int
    advisory_source_count: int
    non_executable_source_count: int
    unsupported_source_count: int
    excluded_source_count: int
    decision_kind_counts: dict[str, int]
    catalog_load_errors: list[str]
    decisions: list[SourceDecision]
    undecided_sources: list[str]
    excluded_sources: list[ExcludedDecision]

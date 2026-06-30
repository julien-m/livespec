# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""Per-source enforcement decisions for the AI-res/ARS convention corpus."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import cast

from validator.conventions_gates import DEFAULT_AST_CATALOGS

from . import source_decision_builders as _builders
from .ars_rules import EXPECTED_ARS_RULE_COUNT, load_ars_executable_rules, project_has_ars_inventory
from .catalog import load_ast_catalogs
from .corpus import SourceClassification, ai_resources_root, build_corpus_manifest
from .source_decision_builders import (
    NOTION_DEFERRED_TASK_ID,
    build_excluded_decision,
    build_source_decision,
    executable_rules_by_source,
)
from .source_decision_types import (
    ExcludedDecision,
    RuleDecisionManifest,
    SourceDecision,
)
from .source_decision_validation import validate_rule_decision_manifest as _validate_manifest


def build_rule_decision_manifest(project_root: Path) -> RuleDecisionManifest:
    """Return one explicit decision per classified AI-res/ARS source."""
    corpus = build_corpus_manifest(project_root)
    root = ai_resources_root(project_root)
    _builders.DEFAULT_AST_CATALOGS = DEFAULT_AST_CATALOGS
    _builders.load_ast_catalogs = load_ast_catalogs
    executable_rules, catalog_errors = executable_rules_by_source(project_root)
    decisions = [
        build_source_decision(root, source, executable_rules, project_root=project_root)
        for source in cast(list[SourceClassification], corpus["sources"])
    ]
    excluded = [build_excluded_decision(root, item) for item in corpus["excluded_sources"]]
    undecided = _undecided_sources(decisions)
    counts: Counter[str] = Counter(decision["rule_decision"]["kind"] for decision in decisions)
    return _manifest_payload(
        project_root, corpus, decisions, excluded, undecided, counts, catalog_errors
    )


def _undecided_sources(decisions: list[SourceDecision]) -> list[str]:
    return [
        decision["source_path"]
        for decision in decisions
        if not decision["rule_decision"]["decision_id"]
    ]


def _manifest_payload(
    project_root: Path,
    corpus: object,
    decisions: list[SourceDecision],
    excluded: list[ExcludedDecision],
    undecided: list[str],
    counts: Counter[str],
    catalog_errors: list[str],
) -> RuleDecisionManifest:
    corpus_data = cast(dict[str, object], corpus)
    return cast(
        RuleDecisionManifest,
        {
            **_ars_rule_level_counts(project_root),
            "total_source_count": cast(int, corpus_data["total_source_count"]),
            "decided_source_count": len(decisions) - len(undecided),
            "undecided_source_count": len(undecided),
            "executable_source_count": counts["executable"],
            "generated_executable_source_count": counts["generated-executable"],
            **_immediate_scope_counts(decisions),
            "deferred_conceptual_editorial_source_count": counts["deferred_conceptual_editorial"],
            "advisory_source_count": counts["advisory"],
            "non_executable_source_count": counts["non-executable"],
            "unsupported_source_count": counts["unsupported"],
            "excluded_source_count": cast(int, corpus_data["excluded_count"]),
            "notion_followup_task_id": NOTION_DEFERRED_TASK_ID,
            "decision_kind_counts": dict(sorted(counts.items())),
            "catalog_load_errors": catalog_errors,
            "decisions": decisions,
            "undecided_sources": undecided,
            "excluded_sources": excluded,
        },
    )


def _ars_rule_level_counts(project_root: Path) -> dict[str, object]:
    if not project_has_ars_inventory(project_root):
        return {
            "rule_level_project_inventory_enabled": False,
            "rule_level_inventory_total_count": 0,
            "rule_level_runtime_rule_count": 0,
            "rule_level_missing_count": 0,
            "rule_level_runtime_rule_ids": [],
        }
    rules = load_ars_executable_rules(project_root)
    observed_count = len(rules)
    return {
        "rule_level_project_inventory_enabled": True,
        "rule_level_inventory_total_count": observed_count,
        "rule_level_runtime_rule_count": observed_count,
        "rule_level_missing_count": EXPECTED_ARS_RULE_COUNT - observed_count,
        "rule_level_runtime_rule_ids": [rule.runtime_rule_id for rule in rules],
    }


def _immediate_scope_counts(decisions: list[SourceDecision]) -> dict[str, int]:
    immediate = [
        decision
        for decision in decisions
        if decision["rule_decision"]["kind"] != "deferred_conceptual_editorial"
    ]
    kinds = Counter(decision["rule_decision"]["kind"] for decision in immediate)
    return {
        "immediate_scope_source_count": len(immediate),
        "immediate_scope_executable_source_count": kinds["executable"],
        "immediate_scope_generated_executable_source_count": kinds["generated-executable"],
        "immediate_scope_non_executable_source_count": len(immediate)
        - kinds["executable"]
        - kinds["generated-executable"],
    }


def validate_rule_decision_manifest(manifest: RuleDecisionManifest) -> list[str]:
    """Return blocking decision-manifest defects."""
    return _validate_manifest(cast(dict[str, object], manifest))

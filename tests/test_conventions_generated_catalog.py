"""Generated-executable catalog decision coverage for feature 073."""

from __future__ import annotations

from pathlib import Path

from validator.conventions_ast.source_decisions import (
    build_rule_decision_manifest,
    validate_rule_decision_manifest,
)


def test_generated_executable_sources_are_explicitly_counted() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())

    assert manifest["total_source_count"] == 192
    assert manifest["generated_executable_source_count"] == 0
    assert manifest["decision_kind_counts"].get("generated-executable", 0) == 0
    assert manifest["undecided_source_count"] == 0
    assert manifest["catalog_load_errors"] == []
    assert validate_rule_decision_manifest(manifest) == []

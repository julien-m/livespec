"""Generated-executable catalog decision coverage for feature 073."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conventions_corpus_fixture import CORPUS_SOURCE_PATHS, convention_corpus_project
from validator.conventions_ast.source_decisions import (
    build_rule_decision_manifest,
    validate_rule_decision_manifest,
)


def test_generated_executable_sources_are_explicitly_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Count the complete synthetic fixture, independently of a private HOME corpus."""
    monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
    manifest = build_rule_decision_manifest(convention_corpus_project(tmp_path))

    assert manifest["total_source_count"] == len(CORPUS_SOURCE_PATHS)
    assert manifest["decided_source_count"] == len(CORPUS_SOURCE_PATHS)
    assert {item["source_path"] for item in manifest["decisions"]} == CORPUS_SOURCE_PATHS
    assert manifest["generated_executable_source_count"] > 0
    assert manifest["decision_kind_counts"].get("generated-executable", 0) > 0
    assert manifest["undecided_source_count"] == 0
    assert manifest["immediate_scope_non_executable_source_count"] == 0
    assert manifest["deferred_conceptual_editorial_source_count"] > 0
    assert manifest["notion_followup_task_id"] == "38fb8415-08de-8130-99a9-eff9a1cf5283"
    assert manifest["catalog_load_errors"] == []
    assert validate_rule_decision_manifest(manifest) == []

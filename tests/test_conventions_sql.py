"""SQL/database source decision coverage for feature 073."""

from __future__ import annotations

from pathlib import Path

from validator.conventions_ast.source_decisions import build_rule_decision_manifest


def test_sql_sources_are_decided_and_non_blocking_until_backend_exists() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    sql_decisions = [
        decision
        for decision in manifest["decisions"]
        if "sql" in decision["languages"] or "database" in decision["domains"]
    ]

    assert sql_decisions
    assert all(decision["rule_decision"]["decision_id"] for decision in sql_decisions)
    assert all(decision["rule_decision"]["missing_capability"] for decision in sql_decisions)
    assert all(not decision["rule_decision"]["rule_ids"] for decision in sql_decisions)
    assert all(
        decision["rule_decision"]["kind"] in {"advisory", "unsupported"}
        for decision in sql_decisions
    )
    assert all(decision["rule_decision"]["non_blocking"] for decision in sql_decisions)

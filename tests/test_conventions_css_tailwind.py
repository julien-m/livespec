"""CSS/Tailwind source decision coverage for feature 073."""

from __future__ import annotations

from pathlib import Path

from validator.conventions_ast.source_decisions import build_rule_decision_manifest


def test_css_and_tailwind_sources_are_decided_without_false_enforcement() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    decisions = manifest["decisions"]
    css_or_tailwind = [
        decision
        for decision in decisions
        if "css" in decision["languages"]
        or "tailwind" in decision["source_path"].lower()
        or "design-tokens" in decision["domains"]
    ]

    assert css_or_tailwind
    assert all(decision["rule_decision"]["decision_id"] for decision in css_or_tailwind)
    assert all(decision["rule_decision"]["missing_capability"] for decision in css_or_tailwind)
    assert all(not decision["rule_decision"]["rule_ids"] for decision in css_or_tailwind)
    assert all(
        decision["rule_decision"]["kind"] in {"advisory", "unsupported", "non-executable"}
        for decision in css_or_tailwind
    )
    assert all(decision["rule_decision"]["non_blocking"] for decision in css_or_tailwind)

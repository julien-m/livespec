"""Executable source-family checks for generated feature 073 decisions."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.conventions_ast.source_decisions import build_rule_decision_manifest
from validator.conventions_ast.source_family_checks import (
    SOURCE_FAMILY_CHECKS,
    evaluate_source_family_fixture,
)

EXPECTED_GENERATED_FAMILIES = {
    "ai_prompt",
    "code_prose",
    "css_design_tokens",
    "database_sql",
    "delphi_code",
    "design_system",
    "go_code",
    "javascript_code",
    "json_yaml_config",
    "markdown_docs",
    "payment_contract",
    "platform_ops",
    "python_code",
    "shell_code",
    "typescript_ui",
}


def test_generated_sources_use_real_family_backends_not_generic_contract() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    generated = [
        decision
        for decision in manifest["decisions"]
        if decision["rule_decision"]["kind"] == "generated-executable"
    ]

    assert generated
    assert all(
        "source-decision-contract" not in decision["rule_decision"]["backend_ids"]
        for decision in generated
    )
    assert {
        family.removeprefix("generated/")
        for decision in generated
        for family in decision["rule_decision"]["fixture_families"]
    } >= EXPECTED_GENERATED_FAMILIES


@pytest.mark.parametrize("family_id", sorted(EXPECTED_GENERATED_FAMILIES))
def test_source_family_checker_fixtures_are_executable(family_id: str) -> None:
    family = SOURCE_FAMILY_CHECKS[family_id]

    assert evaluate_source_family_fixture(family_id, Path(family.pass_fixture)) == []
    violations = evaluate_source_family_fixture(family_id, Path(family.fail_fixture))

    assert violations == [family.detector_id]

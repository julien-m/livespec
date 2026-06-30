"""Executable source-family checks for generated feature 073 decisions."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.conventions_ast.ars_rules import load_ars_executable_rules
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
    family_ids = {
        str(decision["rule_decision"]["generator_id"]).removeprefix("source-family-generator:")
        for decision in generated
    }
    assert family_ids
    assert family_ids <= EXPECTED_GENERATED_FAMILIES


def test_csv_generated_sources_use_ars_rule_level_backends() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    csv_sources = {rule.source_path for rule in load_ars_executable_rules(Path.cwd())}
    generated = [
        decision
        for decision in manifest["decisions"]
        if decision["rule_decision"]["kind"] == "generated-executable"
        and decision["source_path"] in csv_sources
    ]

    assert generated
    assert all(decision["rule_decision"]["backend_ids"] for decision in generated)
    assert all(
        all(
            str(backend).startswith("ars-rule:")
            for backend in decision["rule_decision"]["backend_ids"]
        )
        for decision in generated
    )
    assert all(
        all(
            str(family).startswith("ars_rules/")
            for family in decision["rule_decision"]["fixture_families"]
        )
        for decision in generated
    )


@pytest.mark.parametrize("family_id", sorted(EXPECTED_GENERATED_FAMILIES))
def test_source_family_checker_fixtures_are_executable(family_id: str) -> None:
    family = SOURCE_FAMILY_CHECKS[family_id]

    assert evaluate_source_family_fixture(family_id, Path(family.pass_fixture)) == []
    violations = evaluate_source_family_fixture(family_id, Path(family.fail_fixture))

    assert violations == [family.detector_id]

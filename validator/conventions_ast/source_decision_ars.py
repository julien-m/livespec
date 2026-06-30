# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""ARS rule-level fields for source decision manifests."""

from __future__ import annotations

from pathlib import Path

from .ars_rules import ArsExecutableRule, load_ars_executable_rules, project_has_ars_inventory
from .corpus import SourceClassification
from .source_family_checks import SourceFamilyCheck

GENERATED_SOURCE_TEST = "tests/test_conventions_ars_rules.py"


def source_rules_for(project_root: Path, rel_source_path: str) -> list[ArsExecutableRule]:
    """Return checked-in CSV executable rules keyed to one AI-res source."""
    if not project_has_ars_inventory(project_root):
        return []
    return [
        rule
        for rule in load_ars_executable_rules(project_root)
        if rule.source_path.removeprefix("ai-ressources/") == rel_source_path
    ]


def generated_rule_fields(
    source: SourceClassification,
    family: SourceFamilyCheck,
    source_rules: list[ArsExecutableRule],
) -> dict[str, object]:
    """Return rule/backend/detector/fixture fields for a generated decision."""
    if not source_rules:
        return _family_fields(source, family)
    return {
        "rule_ids": [rule.runtime_rule_id for rule in source_rules],
        "backend_ids": [rule.backend_id for rule in source_rules],
        "detector_ids": [rule.detector_id for rule in source_rules],
        "fixture_families": [_ars_fixture_family(rule) for rule in source_rules],
        "test_ids": [rule.test_id for rule in source_rules],
        "deterministic_test_evidence": [_ars_test_evidence(rule) for rule in source_rules],
    }


def _family_fields(source: SourceClassification, family: SourceFamilyCheck) -> dict[str, object]:
    return {
        "rule_ids": [_generated_rule_id(source["path"]), family.rule_id],
        "backend_ids": [family.backend_id],
        "detector_ids": [family.detector_id],
        "fixture_families": [family.fixture_family],
        "test_ids": [f"pytest:{GENERATED_SOURCE_TEST}::{family.family_id}"],
        "deterministic_test_evidence": [_generated_test_evidence(family)],
    }


def _generated_test_evidence(family: SourceFamilyCheck) -> dict[str, str]:
    return {
        "test": GENERATED_SOURCE_TEST,
        "pass_fixture": family.pass_fixture,
        "fail_fixture": family.fail_fixture,
    }


def _ars_test_evidence(rule: ArsExecutableRule) -> dict[str, str]:
    return {
        "test": "tests/test_conventions_ars_rules.py",
        "pass_fixture": rule.pass_fixture,
        "fail_fixture": rule.fail_fixture,
    }


def _ars_fixture_family(rule: ArsExecutableRule) -> str:
    return str(Path(rule.fail_fixture).parent.relative_to("tests/fixtures/conventions_ast"))


def _generated_rule_id(rel: str) -> str:
    stem = rel.removesuffix(".md").removesuffix(".yaml").removesuffix(".yml")
    slug = "".join(char if char.isalnum() else "." for char in stem.lower())
    return "source." + ".".join(part for part in slug.split(".") if part)

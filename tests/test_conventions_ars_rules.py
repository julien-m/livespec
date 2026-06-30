"""Rule-level executable ARS coverage for feature 073."""

from __future__ import annotations

import shutil
from hashlib import sha256
from pathlib import Path

import pytest

from validator.conventions_ast.ars_rules import (
    EXPECTED_ARS_RULE_COUNT,
    INVENTORY_RELATIVE_PATH,
    ars_rule_by_id,
    detector_for_rule,
    evaluate_ars_rule_fixture,
    load_ars_executable_rules,
    run_ars_executable_rules,
    validate_ars_rule_registry,
)
from validator.conventions_ast.source_decisions import build_rule_decision_manifest
from validator.conventions_feature_scope import SOURCE_SUFFIXES
from validator.conventions_gate import GateSeverity, GateVerdict, verify_conventions


def test_csv_inventory_loads_as_564_individual_runtime_rules() -> None:
    rules = load_ars_executable_rules(Path.cwd())
    detectors = [detector_for_rule(rule) for rule in rules]

    assert len(rules) == EXPECTED_ARS_RULE_COUNT
    assert len({rule.inventory_id for rule in rules}) == EXPECTED_ARS_RULE_COUNT
    assert len({rule.runtime_rule_id for rule in rules}) == EXPECTED_ARS_RULE_COUNT
    assert len({rule.detector_id for rule in rules}) == EXPECTED_ARS_RULE_COUNT
    assert len({id(detector) for detector in detectors}) == EXPECTED_ARS_RULE_COUNT
    assert len({detector.execution_path for detector in detectors}) == (EXPECTED_ARS_RULE_COUNT)
    assert validate_ars_rule_registry(Path.cwd()) == []
    assert all(not rule.backend_id.startswith("source-family:") for rule in rules)
    assert all(not rule.detector_id.startswith("source-family.") for rule in rules)


def test_all_csv_rules_have_pass_fail_fixtures() -> None:
    for rule in load_ars_executable_rules(Path.cwd()):
        assert evaluate_ars_rule_fixture(rule.inventory_id, Path(rule.pass_fixture)) == []
        assert evaluate_ars_rule_fixture(rule.inventory_id, Path(rule.fail_fixture)) == [
            rule.detector_id
        ]


def test_ars_rule_02508_destructive_modal_requires_explicit_confirmation() -> None:
    rule = ars_rule_by_id(Path.cwd())["ARS-RULE-02508"]
    detector = detector_for_rule(rule)

    assert evaluate_ars_rule_fixture(rule.inventory_id, Path(rule.fail_fixture)) == [
        "ars.rule.02508.detector"
    ]
    assert evaluate_ars_rule_fixture(rule.inventory_id, Path(rule.pass_fixture)) == []
    assert not detector(
        "<Dialog><p>Discard local edits?</p>"
        "<button>Cancel</button><button>Close</button><button>Back</button></Dialog>"
    )
    assert detector(
        '<AlertDialog><p>Delete project?</p><Button variant="destructive">OK</Button></AlertDialog>'
    )
    assert detector("<Sheet><p>Remove user access?</p><SheetAction>Yes</SheetAction></Sheet>")
    assert detector("<Dialog><p>Revoke token?</p><DialogAction>Confirm</DialogAction></Dialog>")
    assert not detector(
        "<AlertDialog><p>Delete project?</p>"
        '<Button variant="destructive">Delete project</Button></AlertDialog>'
    )
    violations = run_ars_executable_rules(Path.cwd(), [Path(rule.fail_fixture)])

    assert len(violations) == 1
    assert violations[0].rule_id == rule.runtime_rule_id
    assert violations[0].source == "ars"
    assert "explicit button confirmation" in violations[0].message


def test_language_specific_rules_are_reachable_by_source_suffix_scope() -> None:
    rules = load_ars_executable_rules(Path.cwd())
    unreachable = [
        rule.inventory_id
        for rule in rules
        if rule.language != "language-agnostic"
        and not any(suffix in SOURCE_SUFFIXES for suffix in _language_suffixes(rule.language))
    ]

    assert unreachable == []


@pytest.mark.parametrize("inventory_id", ["ARS-RULE-00321", "ARS-RULE-00515", "ARS-RULE-02484"])
def test_real_project_ars_violations_are_blocking_errors(tmp_path: Path, inventory_id: str) -> None:
    project = _write_ars_project(tmp_path)
    rule = ars_rule_by_id(Path.cwd())[inventory_id]
    source = project / "src" / f"{inventory_id.lower()}{Path(rule.fail_fixture).suffix}"
    source.write_text(Path(rule.fail_fixture).read_text(encoding="utf-8"), encoding="utf-8")

    result = verify_conventions(project)

    assert result.verdict is GateVerdict.FAIL
    assert any(
        violation.rule_id == rule.runtime_rule_id
        and violation.path == source.relative_to(project).as_posix()
        and violation.severity is GateSeverity.ERROR
        for violation in result.violations
    )


def test_rule_decision_manifest_exposes_rule_level_inventory() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())

    assert manifest["rule_level_inventory_total_count"] == EXPECTED_ARS_RULE_COUNT
    assert manifest["rule_level_runtime_rule_count"] == EXPECTED_ARS_RULE_COUNT
    assert manifest["rule_level_missing_count"] == 0
    assert len(manifest["rule_level_runtime_rule_ids"]) == EXPECTED_ARS_RULE_COUNT


def test_generated_decisions_use_ars_rule_backends_not_family_backends() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    csv_sources = {rule.source_path for rule in load_ars_executable_rules(Path.cwd())}
    generated = [
        decision
        for decision in manifest["decisions"]
        if decision["rule_decision"]["kind"] == "generated-executable"
        and decision["source_path"] in csv_sources
    ]

    assert generated
    for decision in generated:
        rule_decision = decision["rule_decision"]
        assert rule_decision["rule_ids"]
        assert all(str(rule_id).startswith("ars.") for rule_id in rule_decision["rule_ids"])
        assert all(
            str(backend_id).startswith("ars-rule:") for backend_id in rule_decision["backend_ids"]
        )
        assert all(
            str(detector_id).startswith("ars.rule.")
            for detector_id in rule_decision["detector_ids"]
        )


def _write_ars_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    constitution = specs / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    constitution_hash = sha256(constitution.read_bytes()).hexdigest()
    gates = specs / "conventions-gates.yaml"
    gates.write_text(
        f"""
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {constitution_hash}
  stack: .specs/stacks/_default.md
commands:
  lint: []
builtin:
  max_file_lines: {{target: 1000, limit: 2000}}
  max_function_lines: {{target: 1000, limit: 2000}}
  file_header: {{}}
  doc_coverage: {{require_public_api: false}}
  token_scale: {{scale: [2, 4, 8, 12, 16], properties: []}}
  suppression_directives: {{budget: 1000, whitelist: []}}
  import_rules: []
coverage: {{}}
exclusions: [".specs/**"]
scope: repo
""",
        encoding="utf-8",
    )
    inventory = tmp_path / INVENTORY_RELATIVE_PATH
    inventory.parent.mkdir(parents=True)
    shutil.copyfile(Path.cwd() / INVENTORY_RELATIVE_PATH, inventory)
    (tmp_path / "src").mkdir()
    return tmp_path


def _language_suffixes(language: str) -> tuple[str, ...]:
    return {
        "css": (".css",),
        "delphi": (".pas", ".dpr", ".dproj"),
        "go": (".go",),
        "javascript": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"),
        "kotlin": (".kt", ".kts"),
        "python": (".py",),
        "rust": (".rs",),
        "shell": (".sh", ".bash", ".zsh"),
        "sql": (".sql",),
        "typescript": (".ts", ".tsx"),
    }.get(language, ())

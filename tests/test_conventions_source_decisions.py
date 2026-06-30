"""Source decision manifest coverage for feature 073.

The ARS source manifest proves classification. These tests prove the second
gate from the approved plan: every classified source has one explicit
enforcement decision, and executable rules carry complete contract metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from typer.testing import CliRunner

from tests.test_conventions_taxonomy import _enforce_project, _write_ai_resources_fixture
from validator.cli import app
from validator.conventions_ast import source_decisions
from validator.conventions_ast.catalog import load_ast_catalog
from validator.conventions_ast.source_decisions import (
    build_rule_decision_manifest,
    validate_rule_decision_manifest,
)
from validator.conventions_ast.taxonomy import taxonomy_fields
from validator.conventions_gate import verify_conventions
from validator.conventions_gates import DEFAULT_AST_CATALOGS, gates_path, generate_conventions_gates
from validator.conventions_receipt import write_conventions_receipt

runner = CliRunner()


def test_rule_decision_manifest_decides_every_classified_source(tmp_path: Path) -> None:
    ai_root = tmp_path / "ai-ressources"
    _write_ai_resources_fixture(ai_root)
    project = _enforce_project(tmp_path / "project", ai_resources_path=ai_root)

    manifest = build_rule_decision_manifest(project)

    assert manifest["total_source_count"] == 10
    assert manifest["decided_source_count"] == 10
    assert manifest["undecided_source_count"] == 0
    assert manifest["excluded_source_count"] == 1
    for decision in manifest["decisions"]:
        assert decision["source_path"].startswith("ai-ressources/")
        assert decision["source_hash"].startswith("sha256:")
        assert decision["source_anchor"]
        assert decision["rule_decision"]["kind"] in {
            "executable",
            "generated-executable",
            "deferred_conceptual_editorial",
        }
        assert decision["rule_decision"]["decision_id"]
        assert decision["rule_decision"]["decision_anchor"]
        assert decision["rule_decision"]["reason"]
        assert decision["rule_decision"]["source_path"] == decision["source_path"]
        assert decision["rule_decision"]["source_hash"] == decision["source_hash"]
        assert decision["rule_decision"]["source_anchor"] == decision["source_anchor"]
        assert decision["rule_decision"]["domain"] in decision["domains"]
        assert decision["rule_decision"]["decision_kind"] == decision["rule_decision"]["kind"]


def test_named_source_decision_has_anchored_reason() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    decision = next(
        item
        for item in manifest["decisions"]
        if item["source_path"] == "ai-ressources/code-conventions/tailwind.md"
    )

    rule_decision = decision["rule_decision"]
    assert rule_decision["kind"] == "generated-executable"
    assert rule_decision["source_anchor"] == decision["source_anchor"]
    assert decision["source_path"] in rule_decision["reason"]
    assert decision["source_anchor"] in rule_decision["reason"]
    assert rule_decision["rule_ids"]
    assert rule_decision["backend_ids"]
    assert rule_decision["detector_ids"]
    assert rule_decision["fixture_families"]
    assert all(str(backend).startswith("ars-rule:") for backend in rule_decision["backend_ids"])
    assert all(str(detector).startswith("ars.rule.") for detector in rule_decision["detector_ids"])
    assert all(
        str(fixture_family).startswith("ars_rules/")
        for fixture_family in rule_decision["fixture_families"]
    )


def test_catalog_load_failure_is_manifest_blocker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    ai_root = tmp_path / "ai-ressources"
    _write_ai_resources_fixture(ai_root)
    project = _enforce_project(tmp_path / "project", ai_resources_path=ai_root)
    monkeypatch.setattr(source_decisions, "DEFAULT_AST_CATALOGS", ("missing-catalog.yaml",))

    manifest = build_rule_decision_manifest(project)

    assert manifest["catalog_load_errors"]
    assert "catalog_load_error:" in validate_rule_decision_manifest(manifest)[0]


def test_validate_rejects_incomplete_executable_metadata(tmp_path: Path) -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    executable = next(
        decision
        for decision in manifest["decisions"]
        if decision["rule_decision"]["kind"] == "executable"
    )
    executable["rule_decision"]["detector_ids"] = []

    issues = validate_rule_decision_manifest(manifest)

    assert any(issue.startswith("missing_detectors:") for issue in issues)


def test_validate_rejects_incomplete_non_blocking_metadata(tmp_path: Path) -> None:
    project = _enforce_project(tmp_path)
    manifest = build_rule_decision_manifest(project)
    non_blocking = next(
        decision
        for decision in manifest["decisions"]
        if decision["rule_decision"]["kind"] == "deferred_conceptual_editorial"
    )
    non_blocking["rule_decision"]["reason"] = ""

    issues = validate_rule_decision_manifest(manifest)

    assert any(issue.startswith("missing_reason:") for issue in issues)


def test_validate_rejects_generated_executable_without_generator_evidence(
    tmp_path: Path,
) -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    executable = next(
        decision
        for decision in manifest["decisions"]
        if decision["rule_decision"]["kind"] == "executable"
    )
    executable["rule_decision"]["kind"] = "generated-executable"
    executable["rule_decision"]["decision_kind"] = "generated-executable"

    issues = validate_rule_decision_manifest(manifest)

    assert any(issue.startswith("missing_generator:") for issue in issues)


def test_taxonomy_fields_expose_rule_decision_manifest(tmp_path: Path) -> None:
    project = _enforce_project(tmp_path)

    fields = taxonomy_fields(project)
    decision_manifest = cast(dict[str, object], fields["rule_decision_manifest"])

    assert decision_manifest["undecided_source_count"] == 0
    assert "decision_kind_counts" in decision_manifest


def test_active_catalog_rules_include_executable_contract_metadata() -> None:
    catalogs = [
        load_ast_catalog(Path(path), project_root=Path.cwd()) for path in DEFAULT_AST_CATALOGS
    ]

    rules = [rule for catalog in catalogs for rule in catalog.rules]
    assert {rule.id for rule in rules} == {
        "ts.no_as_any",
        "ts.no_commonjs_require",
        "rust.no_unwrap",
        "rust.no_expect",
        "rust.no_panic",
        "swift.no_try_force",
        "kotlin.no_unchecked_cast",
    }
    for rule in rules:
        assert rule.decision_kind == "executable"
        assert rule.domain
        assert rule.detector == rule.id
        assert rule.backend
        payload = rule.metadata_payload()
        assert payload["fixture_family"]
        assert payload["fixtures"]
        assert payload["deterministic_test_evidence"]
        payload = rule.metadata_payload()
        assert payload["source_hash"]
        assert payload["source_anchor"]
        assert payload["fixture_family"]
        assert payload["deterministic_test_evidence"]


def test_v1_receipt_serializes_rule_decision_manifest(tmp_path: Path) -> None:
    project = _enforce_project(tmp_path)
    generate_conventions_gates(project, ast_mode="off", force=True)
    result = verify_conventions(project)
    assert result.ast_summary is None

    receipt_path = write_conventions_receipt(
        project_root=project,
        feature_slug="073-conventions-multilang-catalog",
        run_id="source-decisions-v1",
        result=result,
        gates_path=gates_path(project),
    )

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["source_manifest"]["unclassified_count"] == 0
    assert payload["rule_decision_manifest"]["undecided_source_count"] == 0


def test_v1_verify_cli_json_serializes_taxonomy_and_rule_decisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _enforce_project(tmp_path)
    feature_dir = project / ".specs" / "features" / "073-conventions-multilang-catalog"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "| Requirement | File(s) | Last Verified |\n"
        "|---|---|---|\n"
        "| FR-008 | [ok.ts](../../../src/ok.ts) | 2026-06-30 |\n",
        encoding="utf-8",
    )
    generate_conventions_gates(project, ast_mode="off", force=True)
    monkeypatch.setattr(source_decisions, "DEFAULT_AST_CATALOGS", ())

    result = runner.invoke(
        app,
        [
            "conventions",
            "verify",
            "--repo",
            str(project),
            "--feature",
            "073-conventions-multilang-catalog",
            "--run-id",
            "source-decisions-v1-cli",
            "--json",
        ],
    )

    assert result.exit_code in (0, 1), result.output
    payload = json.loads(result.output)
    assert payload["advisory_rules"]
    assert payload["unsupported_rules"]
    assert payload["rule_decision_manifest"]["undecided_source_count"] == 0
    assert payload["rule_decision_manifest"]["immediate_scope_non_executable_source_count"] == 0
    assert (
        payload["rule_decision_manifest"]["notion_followup_task_id"]
        == "38fb8415-08de-8130-99a9-eff9a1cf5283"
    )


def test_v1_verify_cli_blocks_on_broken_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _enforce_project(tmp_path)
    feature_dir = project / ".specs" / "features" / "073-conventions-multilang-catalog"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "| Requirement | File(s) | Last Verified |\n"
        "|---|---|---|\n"
        "| FR-008 | [ok.ts](../../../src/ok.ts) | 2026-06-30 |\n",
        encoding="utf-8",
    )
    generate_conventions_gates(project, ast_mode="off", force=True)
    monkeypatch.setattr(source_decisions, "DEFAULT_AST_CATALOGS", ("missing-catalog.yaml",))

    result = runner.invoke(
        app,
        [
            "conventions",
            "verify",
            "--repo",
            str(project),
            "--feature",
            "073-conventions-multilang-catalog",
            "--run-id",
            "source-decisions-broken-catalog",
            "--json",
        ],
    )

    payload = json.loads(result.output)
    assert result.exit_code == 2
    assert payload["verdict"] == "BLOCKED"
    assert any("catalog_load_error:" in item["message"] for item in payload["blockers"])


def test_catalog_load_error_is_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    from validator.conventions_ast import source_decisions

    def broken_catalogs(*_args: object, **_kwargs: object) -> object:
        from validator.conventions_ast.catalog import AstCatalogError

        raise AstCatalogError("broken catalog")

    monkeypatch.setattr(source_decisions, "load_ast_catalogs", broken_catalogs)

    manifest = build_rule_decision_manifest(Path.cwd())

    assert manifest["catalog_load_errors"] == ["broken catalog"]
    assert "catalog_load_error:broken catalog" in validate_rule_decision_manifest(manifest)


def test_validation_rejects_incomplete_executable_contract() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    decision = next(
        item for item in manifest["decisions"] if item["rule_decision"]["kind"] == "executable"
    )

    decision["rule_decision"]["detector_ids"] = []
    decision["rule_decision"]["test_ids"] = []

    issues = validate_rule_decision_manifest(manifest)
    assert f"missing_detectors:{decision['source_path']}" in issues
    assert f"missing_tests:{decision['source_path']}" in issues


def test_validation_rejects_false_non_executable_rule_wiring() -> None:
    manifest = build_rule_decision_manifest(Path.cwd())
    decision = next(
        item
        for item in manifest["decisions"]
        if item["rule_decision"]["kind"] == "deferred_conceptual_editorial"
    )

    decision["rule_decision"]["missing_capability"] = ""

    issues = validate_rule_decision_manifest(manifest)
    assert f"missing_capability:{decision['source_path']}" in issues
    assert f"missing_notion_deferred_task:{decision['source_path']}" in issues


def test_receipt_and_cli_json_keep_rule_decision_manifest_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _enforce_project(tmp_path)
    generate_conventions_gates(project, ast_mode="off", force=True)
    monkeypatch.setattr(source_decisions, "DEFAULT_AST_CATALOGS", ())
    result = verify_conventions(project)
    receipt_path = write_conventions_receipt(
        project_root=project,
        feature_slug="073-conventions-multilang-catalog",
        run_id="source-decisions-parity",
        result=result,
        gates_path=gates_path(project),
    )

    feature_dir = project / ".specs" / "features" / "073-conventions-multilang-catalog"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implementation.md").write_text(
        "| Requirement | File(s) | Last Verified |\n"
        "|---|---|---|\n"
        "| FR-008 | [ok.ts](../../../src/ok.ts) | 2026-06-30 |\n",
        encoding="utf-8",
    )
    cli = runner.invoke(
        app,
        [
            "conventions",
            "verify",
            "--repo",
            str(project),
            "--feature",
            "073-conventions-multilang-catalog",
            "--run-id",
            "source-decisions-parity-cli",
            "--json",
        ],
    )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload = json.loads(cli.output)
    assert cli.exit_code in (0, 1), cli.output
    assert (
        payload["rule_decision_manifest"]["decision_kind_counts"]
        == receipt["rule_decision_manifest"]["decision_kind_counts"]
    )


def test_receipt_and_cli_json_rule_decision_manifest_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _enforce_project(tmp_path)
    feature_dir = project / ".specs" / "features" / "073-conventions-multilang-catalog"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "| Requirement | File(s) | Last Verified |\n"
        "|---|---|---|\n"
        "| FR-008 | [ok.ts](../../../src/ok.ts) | 2026-06-30 |\n",
        encoding="utf-8",
    )
    generate_conventions_gates(project, ast_mode="off", force=True)
    monkeypatch.setattr(source_decisions, "DEFAULT_AST_CATALOGS", ())

    result = runner.invoke(
        app,
        [
            "conventions",
            "verify",
            "--repo",
            str(project),
            "--feature",
            "073-conventions-multilang-catalog",
            "--run-id",
            "source-decisions-parity",
            "--json",
        ],
    )

    assert result.exit_code in (0, 1), result.output
    payload = json.loads(result.output)
    receipt = json.loads((project / payload["receipt_path"]).read_text(encoding="utf-8"))
    cli_manifest = payload["rule_decision_manifest"]
    receipt_manifest = receipt["rule_decision_manifest"]
    for key in (
        "total_source_count",
        "decided_source_count",
        "undecided_source_count",
        "executable_source_count",
        "generated_executable_source_count",
        "immediate_scope_source_count",
        "immediate_scope_executable_source_count",
        "immediate_scope_generated_executable_source_count",
        "immediate_scope_non_executable_source_count",
        "deferred_conceptual_editorial_source_count",
        "advisory_source_count",
        "non_executable_source_count",
        "unsupported_source_count",
        "excluded_source_count",
        "notion_followup_task_id",
        "decision_kind_counts",
    ):
        assert receipt_manifest[key] == cli_manifest[key]
    nested_decision = next(
        item
        for item in cli_manifest["decisions"]
        if item["source_path"] == "ai-ressources/code-conventions/javascript.md"
    )
    nested = nested_decision["rule_decision"]
    assert nested["decision_id"]
    assert nested["decision_kind"] == nested["kind"]
    assert nested["source_path"] == nested_decision["source_path"]
    assert nested["source_hash"] == nested_decision["source_hash"]
    assert nested["source_anchor"] == nested_decision["source_anchor"]

"""Serialization cases explicitly reexported under their original pytest node IDs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from tests.test_conventions_taxonomy import _enforce_project
from validator.cli import app
from validator.conventions_ast import source_decisions
from validator.conventions_gate import verify_conventions
from validator.conventions_gates import gates_path, generate_conventions_gates
from validator.conventions_receipt import write_conventions_receipt

# @spec FR-003: Preserve CI regression entrypoints — 079-validator-ci-prerequisites
runner = CliRunner()


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

    result = _verify_cli(project, "source-decisions-v1-cli")

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

    result = _verify_cli(project, "source-decisions-broken-catalog")

    payload = json.loads(result.output)
    assert result.exit_code == 2
    assert payload["verdict"] == "BLOCKED"
    assert any("catalog_load_error:" in item["message"] for item in payload["blockers"])


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
    cli = _verify_cli(project, "source-decisions-parity-cli")

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

    result = _verify_cli(project, "source-decisions-parity")

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


def _verify_cli(project: Path, run_id: str) -> Result:
    """Invoke the same CLI boundary for receipt and JSON parity cases."""
    return runner.invoke(
        app,
        [
            "conventions",
            "verify",
            "--repo",
            str(project),
            "--feature",
            "073-conventions-multilang-catalog",
            "--run-id",
            run_id,
            "--json",
        ],
    )

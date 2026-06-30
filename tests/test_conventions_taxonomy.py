"""Receipt taxonomy serialization: advisory_rules[] / unsupported_rules[].

WHY: the release rule (final-plan.md) forbids a PASS that reads as "fully
covered" while heuristic/prose domains (SQL, design, pricing, legal, copy) are
silently absent. The receipt MUST declare those domains as advisory or
unsupported — catalogued, sourced, and explicitly non-blocking (C009 / V10).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from validator.cli import app
from validator.conventions_ast.taxonomy import (
    advisory_rules,
    taxonomy_fields,
    unsupported_rules,
)
from validator.conventions_gate import verify_conventions
from validator.conventions_gates import generate_conventions_gates
from validator.conventions_receipt import verify_conventions_receipt, write_conventions_receipt

runner = CliRunner()


def test_taxonomy_classifies_sql_design_pricing_without_blocking() -> None:
    # WHY: the exact domains the Validator flagged must be present and classed.
    advisory_ids = {entry["id"] for entry in advisory_rules()}
    advisory_domains = {entry["domain"] for entry in advisory_rules()}
    unsupported_domains = {entry["domain"] for entry in unsupported_rules()}

    assert "db.sql.no_select_star" in advisory_ids  # SQL: heuristic, advisory
    assert "design" in advisory_domains  # design tokens: advisory
    assert "pricing" in unsupported_domains  # pricing/MoR: unsupported

    # Every entry is sourced and carries a reason (anti hand-waving).
    for entry in advisory_rules() + unsupported_rules():
        assert entry["reason"]
        assert entry["source_path"]
        assert entry["support_class"] in ("advisory", "unsupported")


def test_taxonomy_fields_shape() -> None:
    fields = taxonomy_fields()
    assert set(fields) == {"advisory_rules", "unsupported_rules"}
    assert fields["advisory_rules"]
    assert fields["unsupported_rules"]


def _enforce_project(tmp_path: Path, ai_resources_path: Path | None = None) -> Path:
    specs = tmp_path / ".specs"
    (specs / "stacks").mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (specs / "stacks" / "_default.md").write_text("# Stack\nTypeScript\n", encoding="utf-8")
    conventions = tmp_path / ".conventions"
    conventions.mkdir()
    if ai_resources_path is None:
        ai_resources_path = tmp_path / "ai-ressources"
        _write_ai_resources_fixture(ai_resources_path)
    (conventions / "manifest.yaml").write_text(
        f"ai_resources_path: {ai_resources_path.as_posix()}\n", encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ok.ts").write_text("const v = input as unknown;\n", encoding="utf-8")
    generate_conventions_gates(tmp_path, ast_mode="enforce")
    return tmp_path


def _write_ai_resources_fixture(root: Path) -> None:
    sources = {
        "code-conventions/javascript.md": "# TypeScript\nNo any.\n",
        "code-conventions/rust.md": "# Rust\nNo unwrap.\n",
        "code-conventions/database.md": "# Database\nAvoid SELECT *.\n",
        "code-conventions/swift-kotlin.md": "# Swift Kotlin\nAvoid force try.\n",
        "architecture/webhook-patterns.md": "# Webhooks\n",
        "design/components/payment-flows.md": "# Payment flows\n",
        "legal/privacy-policy.md": "# Privacy\n",
        "copywriting/landing-page.md": "# Landing\n",
        "pricing-models/usage-based.md": "# Usage pricing\n",
        "stack-ref/databases/postgres.md": "# Postgres SQL\n",
    }
    for rel, text in sources.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "README.md").write_text("# Repo doc\n", encoding="utf-8")


def test_verify_ast_summary_carries_taxonomy(tmp_path: Path) -> None:
    # WHY: taxonomy must ride inside ast_summary so it reaches BOTH the verify
    # JSON and the written receipt. Independent of backend availability.
    project = _enforce_project(tmp_path)
    result = verify_conventions(project)
    assert result.ast_summary is not None
    assert result.ast_summary["advisory_rules"]
    assert result.ast_summary["unsupported_rules"]
    assert result.ast_summary["source_manifest"]


def test_source_manifest_classifies_fixture_without_unclassified_sources(tmp_path: Path) -> None:
    ai_root = tmp_path / "ai-ressources"
    _write_ai_resources_fixture(ai_root)
    project = _enforce_project(tmp_path / "project", ai_resources_path=ai_root)

    fields = taxonomy_fields(project)
    source_manifest = cast(dict[str, object], fields["source_manifest"])

    assert source_manifest["total_source_count"] == 10
    assert source_manifest["classified_count"] == 10
    assert source_manifest["unclassified_count"] == 0
    assert source_manifest["excluded_count"] == 1
    domains = set(cast(dict[str, int], source_manifest["domain_source_counts"]))
    assert {
        "architecture",
        "database",
        "payment",
        "design",
        "legal",
        "copywriting",
        "pricing",
    } <= domains
    matrix = cast(dict[str, list[str]], source_manifest["language_domain_matrix"])
    assert "typescript" in matrix
    assert "rust" in matrix
    assert "sql" in matrix


def test_taxonomy_entries_never_emit_blocking_violations(tmp_path: Path) -> None:
    # WHY (anti false-FAIL/PASS): advisory/unsupported are declarations, not scans;
    # they must never become GateViolations.
    project = _enforce_project(tmp_path)
    result = verify_conventions(project)
    taxonomy_ids = {
        entry["id"] for entry in (*advisory_rules(), *unsupported_rules())
    }
    violation_rules = {v.rule_id for v in result.violations}
    assert taxonomy_ids.isdisjoint(violation_rules)


def test_receipt_serializes_and_round_trips_taxonomy(tmp_path: Path) -> None:
    # WHY: the receipt is the audited artifact; the taxonomy must survive the
    # hash-checked round trip, not just the live JSON.
    project = _enforce_project(tmp_path)
    result = verify_conventions(project)
    from validator.conventions_gates import gates_path

    receipt_path = write_conventions_receipt(
        project_root=project,
        feature_slug="073-conventions-multilang-catalog",
        run_id="taxonomy-check",
        result=result,
        gates_path=gates_path(project),
    )
    import json

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["advisory_rules"]
    assert payload["unsupported_rules"]
    assert payload["source_manifest"]["unclassified_count"] == 0
    # Hash-checked verification must accept the receipt with the extra fields.
    verified = verify_conventions_receipt(
        receipt_path,
        project_root=project,
        expected_feature_slug="073-conventions-multilang-catalog",
    )
    assert verified.verdict in ("PASS", "FAIL", "BLOCKED")


def test_verify_cli_json_exposes_taxonomy_top_level(tmp_path: Path) -> None:
    # WHY: auditors expect advisory_rules/unsupported_rules at the document root
    # of `livespec conventions verify --json`.
    import json

    project = _enforce_project(tmp_path)
    res = runner.invoke(app, ["conventions", "verify", "--repo", str(project), "--json"])
    assert res.exit_code in (0, 2), res.output
    payload = json.loads(res.output)
    assert "advisory_rules" in payload
    assert "unsupported_rules" in payload
    assert payload["source_manifest"]["unclassified_count"] == 0
    assert any(e["id"] == "db.sql.no_select_star" for e in payload["advisory_rules"])

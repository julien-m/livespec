# LiveSpec traceability anchors
# @spec(FR-004)

"""Tests for conventions receipt write and verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.conventions_gate import GateResult, GateVerdict, GateViolation
from validator.conventions_gate_types import GateSeverity
from validator.conventions_receipt import (
    ConventionsReceiptError,
    verify_conventions_receipt,
    write_conventions_receipt,
)


def test_write_and_verify_conventions_receipt(tmp_path: Path) -> None:
    gates = tmp_path / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True)
    gates.write_text("schema_version: 1\n", encoding="utf-8")
    result = GateResult(verdict=GateVerdict.PASS, violations=[], blockers=[])

    receipt_path = write_conventions_receipt(
        project_root=tmp_path,
        feature_slug="061-conventions-gates-engine",
        run_id="run-1",
        result=result,
        gates_path=gates,
    )

    receipt = verify_conventions_receipt(
        receipt_path,
        project_root=tmp_path,
        expected_feature_slug="061-conventions-gates-engine",
    )
    assert receipt.verdict == "PASS"
    assert receipt.gates_sha256


def test_verify_rejects_pass_receipt_with_error_violation(tmp_path: Path) -> None:
    gates = tmp_path / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True)
    gates.write_text("schema_version: 1\n", encoding="utf-8")
    result = GateResult(
        verdict=GateVerdict.FAIL,
        violations=[
            GateViolation(
                rule_id="builtin.max_file_lines",
                path="src/big.py",
                line=1,
                severity="error",
                message="too long",
                source="builtin",
            )
        ],
        blockers=[],
    )
    receipt_path = write_conventions_receipt(
        project_root=tmp_path,
        feature_slug="061-conventions-gates-engine",
        run_id="run-2",
        result=result,
        gates_path=gates,
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["verdict"] = "PASS"
    payload["receipt_hash"] = ""
    receipt_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(ConventionsReceiptError, match=r"verdict_inconsistent|receipt_hash"):
        verify_conventions_receipt(receipt_path, project_root=tmp_path)


def test_verify_rejects_receipt_when_gates_file_changed(tmp_path: Path) -> None:
    gates = tmp_path / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True)
    gates.write_text("schema_version: 1\n", encoding="utf-8")
    result = GateResult(verdict=GateVerdict.PASS, violations=[], blockers=[])
    receipt_path = write_conventions_receipt(
        project_root=tmp_path,
        feature_slug="061-conventions-gates-engine",
        run_id="run-3",
        result=result,
        gates_path=gates,
    )
    gates.write_text("schema_version: 1\nchanged: true\n", encoding="utf-8")

    with pytest.raises(ConventionsReceiptError, match="gates_sha256_mismatch"):
        verify_conventions_receipt(receipt_path, project_root=tmp_path)


def test_write_and_verify_v2_ast_observe_receipt(tmp_path: Path) -> None:
    gates = tmp_path / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True)
    gates.write_text("schema_version: 2\nast_rules:\n  mode: observe\n", encoding="utf-8")
    result = GateResult(
        verdict=GateVerdict.PASS,
        violations=[],
        blockers=[],
        ast_summary={
            "ast_mode": "observe",
            "ast_backend": {"name": "ast-grep", "status": "available", "version": "sg 1.0"},
            "ast_catalogs_sha256": "a" * 64,
            "ast_observations": [
                {
                    "rule_id": "ts.no_as_any",
                    "path": "src/demo.ts",
                    "line": 1,
                    "severity": "error",
                    "message": "as any",
                }
            ],
            "ast_would_fail_count": 1,
        },
    )

    receipt_path = write_conventions_receipt(
        project_root=tmp_path,
        feature_slug="072-conventions-ast-rule-engine",
        run_id="run-ast",
        result=result,
        gates_path=gates,
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt = verify_conventions_receipt(
        receipt_path,
        project_root=tmp_path,
        expected_feature_slug="072-conventions-ast-rule-engine",
    )

    assert payload["schema_version"] == "2"
    assert payload["ast_mode"] == "observe"
    assert payload["ast_would_fail_count"] == 1
    assert receipt.ast_mode == "observe"
    assert receipt.ast_would_fail_count == 1


def test_v2_observe_receipt_rejects_ast_violations(tmp_path: Path) -> None:
    gates = tmp_path / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True)
    gates.write_text("schema_version: 2\nast_rules:\n  mode: observe\n", encoding="utf-8")
    result = GateResult(
        verdict=GateVerdict.FAIL,
        violations=[
            GateViolation(
                rule_id="ts.no_as_any",
                path="src/demo.ts",
                line=1,
                severity=GateSeverity.ERROR,
                message="as any",
                source="ast",
            )
        ],
        blockers=[],
        ast_summary={
            "ast_mode": "observe",
            "ast_backend": {"name": "ast-grep", "status": "available", "version": "sg 1.0"},
            "ast_catalogs_sha256": "a" * 64,
            "ast_observations": [],
            "ast_would_fail_count": 0,
        },
    )
    receipt_path = write_conventions_receipt(
        project_root=tmp_path,
        feature_slug="072-conventions-ast-rule-engine",
        run_id="run-ast-invalid",
        result=result,
        gates_path=gates,
    )

    with pytest.raises(ConventionsReceiptError, match="ast_violation_in_observe"):
        verify_conventions_receipt(receipt_path, project_root=tmp_path)

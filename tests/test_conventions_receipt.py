# LiveSpec traceability anchors
# @spec(FR-004)

"""Tests for conventions receipt write and verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.conventions_gate import GateResult, GateVerdict, GateViolation
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

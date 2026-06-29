"""Tests for mode-aware conventions receipt policy consumers."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from validator.conventions_gate import GateBlocker, GateResult, GateVerdict
from validator.conventions_receipt import write_conventions_receipt
from validator.conventions_receipt_policy import (
    evaluate_conventions_receipt_policy,
)


def _write_gates(project_root: Path, mode: str | None) -> Path:
    gates = project_root / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True, exist_ok=True)
    constitution = project_root / ".specs" / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    if mode is None:
        gates.write_text(
            f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {sha256(constitution.read_bytes()).hexdigest()}
  stack: .specs/stacks/_default.md
""",
            encoding="utf-8",
        )
    else:
        gates.write_text(
            f"""\
schema_version: 2
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {sha256(constitution.read_bytes()).hexdigest()}
  stack: .specs/stacks/_default.md
ast_rules:
  mode: {mode}
""",
            encoding="utf-8",
        )
    return gates


def _write_receipt(
    project_root: Path,
    *,
    mode: str,
    feature_slug: str = "repo",
    verdict: GateVerdict = GateVerdict.PASS,
) -> Path:
    blockers = (
        [GateBlocker(code="ast_backend_unavailable", message="sg unavailable")]
        if verdict == GateVerdict.BLOCKED
        else []
    )
    return write_conventions_receipt(
        project_root=project_root,
        feature_slug=feature_slug,
        run_id=f"run-{feature_slug}-{mode}-{verdict.value.lower()}",
        result=GateResult(
            verdict=verdict,
            violations=[],
            blockers=blockers,
            ast_summary={
                "ast_mode": mode,
                "ast_backend": {"name": "ast-grep", "status": "available", "version": "sg 1.0"},
                "ast_catalogs_sha256": "0" * 64,
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
        ),
        gates_path=project_root / ".specs" / "conventions-gates.yaml",
    )


def test_policy_keeps_v1_and_off_unchanged(tmp_path: Path) -> None:
    _write_gates(tmp_path, None)
    assert evaluate_conventions_receipt_policy(tmp_path, command="doctor").state == "unchanged"

    _write_gates(tmp_path, "off")
    assert evaluate_conventions_receipt_policy(tmp_path, command="spec-check").state == "unchanged"


def test_policy_observe_warns_without_blocking(tmp_path: Path) -> None:
    _write_gates(tmp_path, "observe")
    _write_receipt(tmp_path, mode="observe")

    policy = evaluate_conventions_receipt_policy(tmp_path, command="doctor")

    assert policy.state == "observe_warning"
    assert policy.blocks is False
    assert policy.severity == "WARNING"


def test_policy_enforce_blocks_when_receipt_absent_or_not_pass(tmp_path: Path) -> None:
    _write_gates(tmp_path, "enforce")
    missing = evaluate_conventions_receipt_policy(tmp_path, command="spec-check")
    assert missing.state == "block"
    assert missing.blocks is True
    assert "missing" in missing.reason

    _write_receipt(tmp_path, mode="enforce", verdict=GateVerdict.BLOCKED)
    blocked = evaluate_conventions_receipt_policy(tmp_path, command="spec-check")
    assert blocked.state == "block"
    assert blocked.blocks is True
    assert "BLOCKED" in blocked.reason


def test_policy_ignores_receipts_for_other_features(tmp_path: Path) -> None:
    _write_gates(tmp_path, "enforce")
    _write_receipt(tmp_path, mode="enforce", feature_slug="other-feature")

    policy = evaluate_conventions_receipt_policy(
        tmp_path,
        command="spec-check",
        expected_feature_slug="target-feature",
    )

    assert policy.state == "block"
    assert "missing" in policy.reason


def test_policy_ignores_receipts_from_other_ast_modes(tmp_path: Path) -> None:
    _write_gates(tmp_path, "enforce")
    _write_receipt(tmp_path, mode="observe")

    policy = evaluate_conventions_receipt_policy(tmp_path, command="spec-check")

    assert policy.state == "block"
    assert "missing" in policy.reason

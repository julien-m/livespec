# @spec(AC-001)

"""Tests for RunArtifact receipt re-verification helpers."""

from __future__ import annotations

from pathlib import Path

from validator.conventions_gate import GateBlocker, GateResult, GateVerdict, GateViolation
from validator.conventions_gates import gates_path
from validator.conventions_receipt import write_conventions_receipt
from validator.run_receipts import verify_one_receipt


def _write_gates(project_root: Path) -> Path:
    path = gates_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    constitution = project_root / ".specs" / "constitution.md"
    constitution.parent.mkdir(parents=True, exist_ok=True)
    constitution.write_text("# Constitution\n", encoding="utf-8")
    path.write_text(
        """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 1e573f647f46d0e508830de88db17ac2b096487ad15f73dbd608d5d35640ed94
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions: []
scope: repo
""",
        encoding="utf-8",
    )
    return path


def _write_conventions_receipt(
    project_root: Path,
    *,
    verdict: GateVerdict = GateVerdict.PASS,
) -> Path:
    gates = _write_gates(project_root)
    violations: list[GateViolation] = []
    blockers: list[GateBlocker] = []
    if verdict == GateVerdict.FAIL:
        violations.append(
            GateViolation(
                rule_id="max_file_lines",
                path="src/too_long.py",
                line=501,
                severity="error",
                message="file too long",
                source="builtin",
            )
        )
    if verdict == GateVerdict.BLOCKED:
        blockers.append(GateBlocker(code="tool_missing", message="ruff not found"))
    return write_conventions_receipt(
        project_root=project_root,
        feature_slug="063-conventions-blocking-pipeline",
        run_id=f"run-{verdict.value.lower()}",
        result=GateResult(verdict=verdict, violations=violations, blockers=blockers),
        gates_path=gates,
    )


def test_conventions_receipt_round_trip_verifies(tmp_path: Path) -> None:
    receipt = _write_conventions_receipt(tmp_path)

    check = verify_one_receipt(
        kind="conventions",
        path=receipt.relative_to(tmp_path).as_posix(),
        project_root=tmp_path,
        feature="063-conventions-blocking-pipeline",
    )

    assert check.verified is True
    assert check.kind == "conventions"
    assert check.verdict == "PASS"
    assert check.error is None


def test_conventions_blocked_verdict_is_verified_not_tamper_error(tmp_path: Path) -> None:
    receipt = _write_conventions_receipt(tmp_path, verdict=GateVerdict.BLOCKED)

    check = verify_one_receipt(
        kind="conventions",
        path=receipt.relative_to(tmp_path).as_posix(),
        project_root=tmp_path,
        feature="063-conventions-blocking-pipeline",
    )

    assert check.verified is True
    assert check.verdict == "BLOCKED"
    assert check.error is None


def test_v2_conventions_receipt_round_trip_verifies(tmp_path: Path) -> None:
    gates = _write_gates(tmp_path)
    gates.write_text("schema_version: 2\nast_rules:\n  mode: observe\n", encoding="utf-8")
    receipt = write_conventions_receipt(
        project_root=tmp_path,
        feature_slug="072-conventions-ast-rule-engine",
        run_id="run-ast",
        result=GateResult(
            verdict=GateVerdict.PASS,
            violations=[],
            blockers=[],
            ast_summary={
                "ast_mode": "observe",
                "ast_backend": {"name": "ast-grep", "status": "unavailable", "version": None},
                "ast_catalogs_sha256": "0" * 64,
                "ast_observations": [],
                "ast_would_fail_count": 0,
            },
        ),
        gates_path=gates,
    )

    check = verify_one_receipt(
        kind="conventions",
        path=receipt.relative_to(tmp_path).as_posix(),
        project_root=tmp_path,
        feature="072-conventions-ast-rule-engine",
    )

    assert check.verified is True
    assert check.verdict == "PASS"

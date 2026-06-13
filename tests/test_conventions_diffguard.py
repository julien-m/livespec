"""Tests for conventions supervisor locks: diff guard, hash guard, fresh run."""

from __future__ import annotations

from pathlib import Path

from validator.conventions_diffguard import (
    BaseHashSnapshot,
    FreshGateResult,
    changed_protected_conventions_paths,
    compare_base_hashes,
    supervisor_conventions_gate,
)
from validator.conventions_gate import GateResult, GateVerdict


def _write_gates(project_root: Path, *, extra_config: str = "pyproject.toml") -> None:
    gates = project_root / ".specs" / "conventions-gates.yaml"
    gates.parent.mkdir(parents=True, exist_ok=True)
    gates.write_text(
        f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands:
  lint:
    - id: ruff
      run: ruff check .
      config: {extra_config}
builtin: {{}}
coverage: {{}}
exclusions: []
scope: repo
""",
        encoding="utf-8",
    )
    (project_root / ".specs" / "conventions-rulebook.yaml").write_text(
        "schema_version: 1\ncompiled_at: now\nsources: []\nrules: []\n",
        encoding="utf-8",
    )
    (project_root / extra_config).write_text("[tool.ruff]\n", encoding="utf-8")


def test_protected_conventions_diff_blocks_gate_file_edits(tmp_path: Path) -> None:
    _write_gates(tmp_path)

    blocked = changed_protected_conventions_paths(
        tmp_path,
        changed_paths=[
            ".specs/conventions-gates.yaml",
            "src/app.py",
            "pyproject.toml",
        ],
    )

    assert blocked == [".specs/conventions-gates.yaml", "pyproject.toml"]


def test_base_hash_mismatch_blocks_stale_gate_files(tmp_path: Path) -> None:
    _write_gates(tmp_path)
    snapshot = BaseHashSnapshot(
        gates_sha256="0" * 64,
        rules_sha256="1" * 64,
    )

    blockers = compare_base_hashes(tmp_path, snapshot)

    assert blockers == ["gates_sha256_mismatch", "rules_sha256_mismatch"]


def test_supervisor_uses_fresh_verdict_over_stale_worker_receipt(tmp_path: Path) -> None:
    _write_gates(tmp_path)
    stale_receipt = {"kind": "conventions", "verified": True, "verdict": "PASS"}

    result = supervisor_conventions_gate(
        tmp_path,
        worker_receipt=stale_receipt,
        run_verify=lambda root: GateResult(verdict=GateVerdict.FAIL, violations=[], blockers=[]),
    )

    assert result == FreshGateResult(
        verdict="FAIL",
        source="fresh_supervisor_run",
        stale_worker_verdict="PASS",
    )

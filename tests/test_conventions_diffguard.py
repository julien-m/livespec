# @spec(AC-013)
# @spec(AC-014)
# @spec(AC-015)

"""Tests for conventions supervisor locks: diff guard, hash guard, fresh run."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.cli_commands import conventions_cmd
from validator.conventions_diffguard import (
    BaseHashSnapshot,
    FreshGateResult,
    changed_protected_conventions_paths,
    compare_base_hashes,
    supervisor_conventions_gate,
)
from validator.conventions_feature_scope import FeatureScope
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


def _stub_supervisor_diff_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(conventions_cmd, "git_changed_paths", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        conventions_cmd,
        "changed_protected_conventions_paths",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        conventions_cmd,
        "base_hash_snapshot",
        lambda *_args, **_kwargs: BaseHashSnapshot(gates_sha256="", rules_sha256=""),
    )
    monkeypatch.setattr(conventions_cmd, "compare_base_hashes", lambda *_args, **_kwargs: [])


def _conventions_receipt(**overrides: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "oracle": "livespec-conventions-gate",
        "schema_version": "1",
        "verdict": "PASS",
        "source_manifest": {},
        "rule_decision_manifest": {},
    }
    receipt.update(overrides)
    return receipt


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
    stale_receipt = _conventions_receipt()

    result = supervisor_conventions_gate(
        tmp_path,
        worker_receipt=stale_receipt,
        run_verify=lambda root, feature_slug: GateResult(
            verdict=GateVerdict.FAIL,
            violations=[],
            blockers=[],
        ),
    )

    assert result == FreshGateResult(
        verdict="FAIL",
        source="fresh_supervisor_run",
        stale_worker_verdict="PASS",
    )


def test_supervisor_uses_feature_scope_from_worker_receipt(tmp_path: Path) -> None:
    _write_gates(tmp_path)
    receipt = _conventions_receipt(
        feature_slug="073-conventions-multilang-catalog",
        run_id="validator-073-final-20260630",
    )
    calls: list[str | None] = []

    def run_verify(_root: Path, feature_slug: str | None) -> GateResult:
        calls.append(feature_slug)
        verdict = GateVerdict.PASS if feature_slug == receipt["feature_slug"] else GateVerdict.FAIL
        return GateResult(verdict=verdict, violations=[], blockers=[])

    result = supervisor_conventions_gate(tmp_path, worker_receipt=receipt, run_verify=run_verify)

    assert result.verdict == "PASS"
    assert result.source == "fresh_supervisor_run"
    assert result.stale_worker_verdict == "PASS"
    assert calls == ["073-conventions-multilang-catalog"]


def test_supervisor_feature_scope_uses_fresh_fail_over_stale_pass(tmp_path: Path) -> None:
    _write_gates(tmp_path)
    receipt = _conventions_receipt(
        feature_slug="073-conventions-multilang-catalog",
        run_id="validator-073-final-20260630",
    )

    result = supervisor_conventions_gate(
        tmp_path,
        worker_receipt=receipt,
        run_verify=lambda _root, _feature_slug: GateResult(
            verdict=GateVerdict.FAIL,
            violations=[],
            blockers=[],
        ),
    )

    assert result.verdict == "FAIL"
    assert result.stale_worker_verdict == "PASS"


def test_supervisor_preserves_repo_scope_without_feature_receipt(tmp_path: Path) -> None:
    _write_gates(tmp_path)
    calls: list[str | None] = []

    def run_verify(_root: Path, feature_slug: str | None) -> GateResult:
        calls.append(feature_slug)
        return GateResult(verdict=GateVerdict.FAIL, violations=[], blockers=[])

    result = supervisor_conventions_gate(
        tmp_path,
        worker_receipt={"kind": "conventions", "verified": True, "verdict": "PASS"},
        run_verify=run_verify,
    )

    assert result.verdict == "FAIL"
    assert calls == [None]


def test_supervisor_ignores_feature_scope_from_non_conventions_receipt(tmp_path: Path) -> None:
    _write_gates(tmp_path)
    calls: list[str | None] = []

    def run_verify(_root: Path, feature_slug: str | None) -> GateResult:
        calls.append(feature_slug)
        return GateResult(verdict=GateVerdict.PASS, violations=[], blockers=[])

    result = supervisor_conventions_gate(
        tmp_path,
        worker_receipt={"verdict": "PASS", "feature_slug": "073-conventions-multilang-catalog"},
        run_verify=run_verify,
    )

    assert result.verdict == "PASS"
    assert result.stale_worker_verdict == "PASS"
    assert calls == [None]


def test_supervisor_cli_feature_receipt_runs_fresh_feature_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_gates(tmp_path)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(
        """\
{
  "oracle": "livespec-conventions-gate",
  "schema_version": 1,
  "verdict": "PASS",
  "feature_slug": "073-conventions-multilang-catalog",
  "run_id": "run-073",
  "source_manifest": {},
  "rule_decision_manifest": {}
}
""",
        encoding="utf-8",
    )
    expected_scope = FeatureScope(
        feature_slug="073-conventions-multilang-catalog",
        paths=frozenset({"validator/conventions_diffguard.py"}),
    )
    _stub_supervisor_diff_guards(monkeypatch)
    monkeypatch.setattr(
        conventions_cmd,
        "resolve_feature_scope",
        lambda _root, feature_slug: expected_scope
        if feature_slug == "073-conventions-multilang-catalog"
        else None,
    )

    def verify(
        _root: Path,
        *,
        feature_scope: FeatureScope | None = None,
        **_kwargs: object,
    ) -> GateResult:
        verdict = GateVerdict.PASS if feature_scope == expected_scope else GateVerdict.FAIL
        return GateResult(verdict=verdict, violations=[], blockers=[])

    monkeypatch.setattr(conventions_cmd, "verify_conventions", verify)

    payload, exit_code = conventions_cmd._build_supervisor_gate_payload(
        tmp_path,
        base_ref="main",
        head_ref="HEAD",
        worker_receipt=receipt_path,
    )

    assert exit_code == 0
    assert payload["verdict"] == "PASS"
    assert payload["stale_worker_verdict"] == "PASS"

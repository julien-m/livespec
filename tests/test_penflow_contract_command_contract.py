"""Command documentation tests for the Penflow UI contract integration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_system_penflow_contract_doc_exists() -> None:
    body = _read("system/testing/penflow-contract.md")

    assert "Penflow Contract Verdict: PASS | FAIL | BLOCKED | ABSENT" in body
    assert "penflow/semantic-ui-tree.json" in body
    assert "top-level `verdict`" in body
    assert "--require-actual" in body
    assert "runtime_comparison: BLOCKED" in body
    assert "screenshots remain visual regression gates" in body


def test_spec_init_supports_brainstorm_and_from_scratch_penflow() -> None:
    body = _read(".agent-sync/skills/spec-init/SKILL.md")

    assert "Step 3.5.5 — Penflow Contract Workspace Bootstrap" in body
    assert ".brainstorm/penflow/" in body
    assert "copy it to root `penflow/`" in body
    assert "continue from scratch" in body
    assert "state: absent" in body


def test_ui_commands_reference_penflow_contract_artifacts() -> None:
    specify = _read(".agent-sync/skills/spec-specify/SKILL.md")
    plan = _read(".agent-sync/skills/spec-plan/SKILL.md")
    implement = _read(".agent-sync/skills/spec-implement/SKILL.md")
    test = _read(".agent-sync/skills/spec-test/SKILL.md")
    check = _read(".agent-sync/skills/spec-check/SKILL.md")

    assert "penflow/semantic-ui-tree.json" in specify
    assert "flow_id" in specify and "screen_id" in specify
    assert "penflow/code-ir.json" in plan
    assert "penflow/expected-ui-tree.json" in implement
    assert "Penflow Contract Gate" in test
    assert "--require-actual" in test
    assert "penflow compare-tree" in test
    assert "Penflow Contract Status" in check
    assert "do not read `.brainstorm/`" in check


def test_command_expectations_include_penflow_verdicts() -> None:
    for skill in ("spec-init", "spec-specify", "spec-plan"):
        body = _read(f".agent-sync/skills/{skill}/expectations.md")
        assert "Penflow Contract Verdict: ABSENT | BLOCKED | PASS" in body

    for skill in ("spec-implement", "spec-test", "spec-check"):
        body = _read(f".agent-sync/skills/{skill}/expectations.md")
        assert "Penflow Contract Verdict: ABSENT | PASS | FAIL | BLOCKED" in body

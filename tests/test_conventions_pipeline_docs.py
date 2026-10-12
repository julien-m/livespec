# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-008)
# @spec(AC-009)
# @spec(FR-007)

"""Static contract tests for conventions blocking pipeline command docs."""

# @spec(FR-003)

from __future__ import annotations

from pathlib import Path

from validator.expectations import parse_expectations

REPO_ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_expectations_require_conventions_receipt_verdict_rule() -> None:
    expected = {"kind": "conventions", "verdict": "PASS", "required_if_exists": True}
    for command in ("spec-implement", "spec-test", "spec-fix", "spec-feature", "spec-ship"):
        parsed = parse_expectations(REPO_ROOT / f".agent-sync/skills/{command}/expectations.md")
        rules = [rule.payload for rule in parsed.verify.must if rule.kind == "receipt_verdict"]
        assert rules == [expected], command


def test_final_command_skills_verify_conventions_before_phase_result() -> None:
    for command in ("spec-implement", "spec-test", "spec-fix"):
        text = _text(f".agent-sync/skills/{command}/SKILL.md")
        assert "livespec conventions verify --json --feature <slug>" in text
        assert "receipt_path" in text
        assert "conventions_receipt_path" in text
        assert "PHASE_RESULT: BLOCKED - conventions_gate_failed" in text
        assert "extra.conventions_verdict" in text
        assert "extra.conventions_receipt_path" in text


def test_spec_fix_documents_conventions_burndown_mode() -> None:
    text = _text(".agent-sync/skills/spec-fix/SKILL.md")

    assert "--conventions" in text
    assert "debt.json" in text
    assert "verify --report" in text
    assert "worst-first" in text
    assert "strictly decreasing" in text
    assert "zero new violations" in text


def test_agent_prompts_treat_conventions_gate_as_blocking() -> None:
    verifier = _text(".agent-sync/agents/livespec-verifier/prompt.md")
    supervisor = _text(".agent-sync/agents/livespec-supervisor/prompt.md")

    assert "conventions gate failure is BLOCKING when gates file exists" in verifier
    assert "conventions receipt PASS (repo scope) is a hard gate" in supervisor
    assert "pre-existing" in supervisor
    assert "pre-existing" in verifier
    assert "never justifies skipping conventions" in supervisor
    assert "never justifies skipping conventions" in verifier


def test_evidence_first_retry_contract_is_documented_for_goal_locked_commands() -> None:
    anti_drift = _text("system/anti-drift-block.md")

    assert "Evidence-first retry contract" in anti_drift
    assert "retry_hypothesis" in anti_drift
    assert "retry_evidence" in anti_drift
    assert "retry_result" in anti_drift
    assert "write_stdin" in anti_drift

    for command in (
        "spec-check",
        "spec-feature",
        "spec-fix",
        "spec-implement",
        "spec-plan",
        "spec-test",
    ):
        text = _text(f".agent-sync/skills/{command}/SKILL.md")
        assert "Evidence-First Retry Contract" in text
        assert "retry_hypothesis" in text
        assert "retry_evidence" in text
        assert "retry_result" in text

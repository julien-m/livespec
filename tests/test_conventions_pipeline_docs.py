"""Static contract tests for conventions blocking pipeline command docs."""

from __future__ import annotations

from pathlib import Path

from tests.test_goal_contracts import EXPECTATIONS
from validator.expectations import parse_expectations

REPO_ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_expectations_require_conventions_receipt_verdict_rule() -> None:
    for command in ("spec-implement", "spec-test", "spec-fix", "spec-feature", "spec-ship"):
        text = _text(f".agent-sync/skills/{command}/expectations.md")
        assert "last_reviewed: 2026-06-13" in text
        assert 'receipt_verdict: {"kind": "conventions", "verdict": "PASS"' in text


def test_final_command_skills_verify_conventions_before_phase_result() -> None:
    for command in ("spec-implement", "spec-test", "spec-fix"):
        text = _text(f".agent-sync/skills/{command}/SKILL.md")
        assert "livespec conventions verify --json --feature <slug>" in text
        assert "PHASE_RESULT: BLOCKED - conventions_gate_failed" in text
        assert "extra.conventions_verdict" in text


def test_spec_fix_documents_conventions_burndown_mode() -> None:
    text = _text(".agent-sync/skills/spec-fix/SKILL.md")

    assert "--conventions" in text
    assert "debt.json" in text
    assert "verify --report" in text
    assert "worst-first" in text
    assert "strictly decreasing" in text
    assert "zero new violations" in text


def test_python_ruff_template_enables_pylint_rules_without_file_length_as_line_width() -> None:
    rendered = _text("templates/conventions/python_ruff.toml.tmpl")
    rendered = rendered.replace("{{max_file_lines}}", "500")
    rendered = rendered.replace("{{max_function_lines}}", "60")

    assert 'select = ["E", "F", "I", "PLR"]' in rendered
    assert "line-length = 500" not in rendered


def test_agent_prompts_treat_conventions_gate_as_blocking() -> None:
    verifier = _text(".agent-sync/agents/livespec-verifier/prompt.md")
    supervisor = _text(".agent-sync/agents/livespec-supervisor/prompt.md")

    assert "conventions gate failure is BLOCKING when gates file exists" in verifier
    assert "conventions receipt PASS (repo scope) is a hard gate" in supervisor
    assert "pre-existing" in supervisor
    assert "pre-existing" in verifier
    assert "never justifies skipping conventions" in supervisor
    assert "never justifies skipping conventions" in verifier


def test_expectations_parser_accepts_receipt_verdict_rule(tmp_path: Path) -> None:
    expectations = EXPECTATIONS.replace(
        "    - exit_code: 0",
        '    - receipt_verdict: {"kind": "conventions", "verdict": "PASS", '
        '"required_if_exists": true}',
    )
    path = tmp_path / "expectations.md"
    path.write_text(expectations, encoding="utf-8")

    parsed = parse_expectations(path)

    assert parsed.verify.must[0].kind == "receipt_verdict"
    assert parsed.verify.must[0].payload == {
        "kind": "conventions",
        "verdict": "PASS",
        "required_if_exists": True,
    }

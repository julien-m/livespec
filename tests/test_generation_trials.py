"""Deterministic trial mechanics; these transport doubles never measure model quality."""

from pathlib import Path

import pytest

from tests.integration.helpers import witness_generation
from tests.integration.helpers.witness_evaluator import FIXTURES
from tests.integration.helpers.witness_process import ProcessCapture


def test_unavailable_runtime_records_not_run_without_an_attempt(monkeypatch) -> None:
    monkeypatch.setattr(witness_generation.shutil, "which", lambda runtime: None)
    result = witness_generation.run_generation_trial("python-purge", "codex")
    assert result.outcome == "not_run" and result.attempts == 0
    assert result.measured_cost_usd is None


@pytest.mark.parametrize("attempts", (0, 3))
def test_trial_attempt_bound_is_enforced(attempts: int) -> None:
    with pytest.raises(ValueError, match="at most one repair"):
        witness_generation.run_generation_trial("python-purge", "codex", max_attempts=attempts)


def test_one_repair_is_distinct_from_first_attempt_success(monkeypatch) -> None:
    attempted: list[Path] = []
    source = (FIXTURES / "witness-python-purge/seed/purge.py").read_text()
    monkeypatch.setattr(witness_generation.shutil, "which", lambda runtime: "codex")

    def generate(argv, cwd, timeout_sec):
        if "--version" in argv:
            return ProcessCapture(0, "test transport", "", 0)
        attempted.append(cwd)
        code = source.replace("path.unlink()", "pass") if len(attempted) == 1 else source
        (cwd / "purge.py").write_text(code)
        return ProcessCapture(0, "", "", 0)

    monkeypatch.setattr(witness_generation, "run_process", generate)
    result = witness_generation.run_generation_trial("python-purge", "codex")
    assert result.outcome == "repaired_success" and result.attempts == 2
    assert result.evaluation and result.evaluation.assertions == 4
    assert not attempted[0].exists(), "workspace is released only after oracle evaluation"


@pytest.mark.parametrize("tamper", (False, True))
def test_process_success_does_not_prove_missing_candidate_or_changed_contract(
    monkeypatch, tamper: bool
) -> None:
    monkeypatch.setattr(witness_generation.shutil, "which", lambda runtime: "codex")

    def generate(argv, cwd, timeout_sec):
        if "--version" not in argv and tamper:
            (cwd / "contract.md").write_text("Pretend every result is correct")
        return ProcessCapture(0, "all requirements passed", "", 0)

    monkeypatch.setattr(witness_generation, "run_process", generate)
    result = witness_generation.run_generation_trial("python-purge", "codex", max_attempts=1)
    assert result.outcome == ("invalid" if tamper else "failure")


@pytest.mark.parametrize(
    ("runtime", "events", "model", "cost"),
    [
        ("codex", '{"model":"controlled-codex","total_cost_usd":0.125}', "controlled-codex", 0.125),
        (
            "claude",
            '{"modelUsage":{"controlled-claude":{}},"total_cost_usd":0.25}',
            "controlled-claude",
            0.25,
        ),
        ("codex", "{}", None, None),
    ],
)
def test_first_attempt_reports_observed_capture_fields(
    tmp_path,
    monkeypatch,
    runtime,
    events,
    model,
    cost,
):
    import json
    import time

    source = (FIXTURES / "witness-python-purge/seed/purge.py").read_text()
    attempts = []
    monkeypatch.setattr(witness_generation.shutil, "which", lambda _: runtime)

    def generate(argv, cwd, timeout_sec):
        if "--version" in argv:
            return ProcessCapture(0, "controlled-cli 1.2\n", "", 0.001)
        attempts.append(tuple(argv))
        (cwd / "purge.py").write_text(source)
        return ProcessCapture(0, events, "", 0.003, argv=tuple(argv))

    monkeypatch.setattr(witness_generation, "run_process", generate)
    report = tmp_path / "trial.json"
    started = time.monotonic()
    result = witness_generation.run_generation_trial(
        "python-purge",
        runtime,
        max_attempts=1,
        report_path=report,
    )
    elapsed = time.monotonic() - started
    payload = json.loads(report.read_text())
    assert result.outcome == "first_attempt_success" and result.attempts == len(attempts) == 1
    assert result.evaluation and result.evaluation.assertions == 4
    assert 0 < result.duration_sec <= elapsed
    assert result.runtime == runtime and result.runtime_version == "controlled-cli 1.2"
    assert result.model == model and result.measured_cost_usd == cost
    assert result.generation[0].argv == attempts[0]
    assert payload["duration_sec"] == result.duration_sec
    assert payload["model"] == model and payload["measured_cost_usd"] == cost


def test_terminal_behavior_failure_preserves_attempt_count_and_unknown_cost(monkeypatch):
    source = (FIXTURES / "witness-python-purge/seed/purge.py").read_text()
    calls = []
    monkeypatch.setattr(witness_generation.shutil, "which", lambda _: "codex")

    def generate(argv, cwd, timeout_sec):
        if "--version" in argv:
            return ProcessCapture(0, "controlled-cli", "", 0)
        calls.append(cwd)
        (cwd / "purge.py").write_text(source.replace("path.unlink()", "pass"))
        return ProcessCapture(0, '{"model":"controlled-codex"}', "", 0)

    monkeypatch.setattr(witness_generation, "run_process", generate)
    result = witness_generation.run_generation_trial("python-purge", "codex", max_attempts=2)
    assert result.outcome == "failure" and result.attempts == len(calls) == 2
    assert result.evaluation and not result.evaluation.behavior_passed
    assert result.reason == "behavioral_assertion_failed"
    assert result.duration_sec > 0 and result.model == "controlled-codex"
    assert result.measured_cost_usd is None and not result.timed_out


@pytest.mark.parametrize("bypass", (False, True))
def test_expected_unauthorized_block_is_decided_by_external_http_oracle(
    tmp_path,
    monkeypatch,
    bypass,
):
    import json

    source = (FIXTURES / "witness-typescript-api/seed/app.ts").read_text()
    if bypass:
        source = source.replace('!== "Bearer witness"', '=== "never"')
    monkeypatch.setattr(witness_generation.shutil, "which", lambda _: "codex")

    def generate(argv, cwd, timeout_sec):
        if "--version" in argv:
            return ProcessCapture(0, "controlled-cli", "", 0)
        (cwd / "app.ts").write_text(source)
        return ProcessCapture(0, '{"model":"controlled-codex"}', "", 0)

    monkeypatch.setattr(witness_generation, "run_process", generate)
    report = tmp_path / "trial.json"
    result = witness_generation.run_generation_trial(
        "typescript-api",
        "codex",
        scenario="unauthorized",
        max_attempts=1,
        report_path=report,
    )
    assert result.scenario == "unauthorized" and result.attempts == 1
    assert result.evaluation and result.evaluation.capture
    assert result.evaluation.capture.argv[-1] == "unauthorized"
    if bypass:
        assert result.outcome == "failure" and not result.evaluation.behavior_passed
    else:
        assert result.outcome == "correct_blocked" and result.evaluation.behavior_passed
        assert result.evaluation.assertions == 2
        assert result.reason == "expected_unauthorized_request_blocked"
    assert json.loads(report.read_text())["outcome"] == result.outcome


@pytest.mark.parametrize("available", (False, True))
def test_expected_block_does_not_relabel_missing_runtime_or_runtime_failure(monkeypatch, available):
    monkeypatch.setattr(
        witness_generation.shutil, "which", lambda _: "codex" if available else None
    )
    monkeypatch.setattr(
        witness_generation,
        "run_process",
        lambda *a: ProcessCapture(2, "BLOCKED", "runtime error", 0),
    )
    result = witness_generation.run_generation_trial(
        "typescript-api",
        "codex",
        scenario="unauthorized",
        max_attempts=1,
    )
    assert result.outcome == ("failure" if available else "not_run")
    assert result.attempts == (1 if available else 0)
    assert result.evaluation is None


def test_expected_block_scope_is_selected_and_validated_before_generation():
    with pytest.raises(ValueError, match="Only the API unauthorized"):
        witness_generation.run_generation_trial("python-purge", "codex", scenario="unauthorized")


def test_full_api_trial_retains_success_scope_and_six_checks(monkeypatch):
    source = (FIXTURES / "witness-typescript-api/seed/app.ts").read_text()
    monkeypatch.setattr(witness_generation.shutil, "which", lambda _: "codex")

    def generate(argv, cwd, timeout_sec):
        if "--version" in argv:
            return ProcessCapture(0, "controlled-cli", "", 0)
        (cwd / "app.ts").write_text(source)
        return ProcessCapture(0, "", "", 0)

    monkeypatch.setattr(witness_generation, "run_process", generate)
    result = witness_generation.run_generation_trial("typescript-api", "codex", max_attempts=1)
    assert result.scenario == "full" and result.outcome == "first_attempt_success"
    assert result.evaluation and result.evaluation.assertions == 6

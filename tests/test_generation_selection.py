# @spec(AC-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#ac-013
"""Coverage selection cannot manufacture completed or cross-runtime evidence."""

from tests.integration.helpers.generation_selection import coverage_report, select_generation
from tests.integration.helpers.witness_evaluator import Evaluation
from tests.integration.helpers.witness_generation import TrialResult
from tests.integration.helpers.witness_process import ProcessCapture


def test_core_sample_and_full_runtime_matrix_are_explicit() -> None:
    assert select_generation(["README.md"]).witnesses == ()
    sample = select_generation(["validator/semantic/plan_review.py"])
    assert sample.witnesses == ("python-purge",)
    full = select_generation([], full=True, runtimes=("claude", "codex"))
    result = TrialResult("python-purge", "claude", "first_attempt_success", attempts=1)
    report = coverage_report(full, [result])
    assert not report["complete"]
    assert isinstance(report["rows"], list)
    assert len(report["rows"]) == 6
    assert result.measured_cost_usd is None


def test_unavailable_or_duplicate_trials_are_not_completed() -> None:
    selection = select_generation([".agent-sync/skills/spec-feature/SKILL.md"])
    unavailable = TrialResult("python-purge", "claude", "not_run", reason="runtime_unavailable")
    assert not coverage_report(selection, [unavailable])["complete"]
    passed = TrialResult("python-purge", "claude", "first_attempt_success", attempts=1)
    assert not coverage_report(selection, [passed, passed])["complete"]
    assert not coverage_report(selection, [passed])["complete"]
    passed.oracle_sha256 = "a" * 64
    passed.evaluation = Evaluation("pass", True, "oracle", 4, ProcessCapture(0, "", "", 1))
    assert coverage_report(selection, [passed])["complete"]
    passed.stage = "spec_feature_pipeline"
    assert not coverage_report(selection, [passed])["complete"]


def test_model_runtime_changes_select_full_corpus() -> None:
    result = select_generation(["validator/llm_provider.py"])
    assert result.mode == "full"
    assert len(result.witnesses) == 3


def test_receipt_changes_sample_and_native_runner_changes_require_full() -> None:
    assert select_generation(["validator/evidence_receipts.py"]).mode == "sample"
    assert select_generation(["tests/integration/helpers/witness_process.py"]).mode == "full"

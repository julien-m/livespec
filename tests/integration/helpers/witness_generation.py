# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""Bound real native generation trials and independently evaluate each candidate."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from tests.integration.helpers.witness_evaluator import (
    FIXTURES,
    Evaluation,
    FrozenOracle,
    evaluate_candidate,
    freeze_oracle,
)
from tests.integration.helpers.witness_process import ProcessCapture, run_process
from tests.integration.helpers.witness_runtime import generation_arguments as generation_arguments
from tests.integration.helpers.witness_snapshot import (
    _observed_metadata,
    candidate_identity,
    capture_candidate_sources,
)
from tests.integration.helpers.witness_workspace import WitnessWorkspace

Outcome = Literal[
    "first_attempt_success",
    "repaired_success",
    "correct_blocked",
    "failure",
    "invalid",
    "not_run",
    "evidence_incomplete",
]


@dataclass
class TrialResult:
    """Observed results; nullable model/cost never become invented measurements."""

    witness: str
    runtime: str
    outcome: Outcome
    attempts: int = 0
    duration_sec: float = 0
    model: str | None = None
    measured_cost_usd: float | None = None
    runtime_version: str | None = None
    timed_out: bool = False
    reason: str = ""
    evaluation: Evaluation | None = None
    generation: list[ProcessCapture] = field(default_factory=list)
    oracle_sha256: str = ""
    stage: str = "native_code_generation"
    scenario: str = "full"
    pipeline_verified: bool = False
    penflow_diagnostic: str | None = None
    candidate_sha256: dict[str, str] = field(default_factory=dict)
    candidate_sources: dict[str, str] = field(default_factory=dict)
    retained_workspace: str | None = None
    execution_control: str = "observed_local_processes"

    def to_dict(self) -> dict[str, object]:
        """Serialize actual captures for persistent evaluation reports."""
        return asdict(self)


def run_generation_trial(
    witness: str,
    runtime: str,
    *,
    timeout_sec: float = 180,
    max_attempts: int = 2,
    report_path: Path | None = None,
    max_budget_usd: float = 5,
    prepared_ui_candidate: Path | None = None,
    scenario: str = "full",
) -> TrialResult:
    """Generate in a retained disposable workspace; evaluator owns the oracle throughout."""
    if max_attempts not in (1, 2) or timeout_sec <= 0:
        raise ValueError("Trials allow one initial attempt and at most one repair; timeout > 0")
    oracle = freeze_oracle(witness, scenario=scenario)
    if prepared_ui_candidate is not None:
        if witness != "ui-form" or report_path is None:
            raise ValueError("Prepared UI requires the UI witness and an external report path")
        from tests.integration.helpers.witness_prepared_ui import run_prepared_ui_trial

        return run_prepared_ui_trial(
            prepared_ui_candidate,
            runtime,
            timeout_sec=timeout_sec,
            max_attempts=max_attempts,
            report_path=report_path,
            max_budget_usd=max_budget_usd,
        )
    result = TrialResult(
        witness, runtime, "not_run", oracle_sha256=oracle.sha256, scenario=oracle.scenario
    )
    executable = shutil.which(runtime)
    if executable is None:
        result.reason = "runtime_unavailable"
    else:
        _run_disposable(
            result, oracle, executable, timeout_sec, max_attempts, report_path, max_budget_usd
        )
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
    return result


def _run_disposable(
    result: TrialResult,
    oracle: FrozenOracle,
    executable: str,
    timeout_sec: float,
    max_attempts: int,
    report_path: Path | None,
    max_budget_usd: float,
) -> None:
    """Keep candidate ownership through evaluation and preserve uncontrolled runs."""
    started = time.monotonic()
    version = run_process([executable, "--version"], FIXTURES, 10)
    result.runtime_version = version.stdout.strip() or None
    with WitnessWorkspace(prefix="livespec_witness_candidate_") as workspace:
        root = workspace.root
        candidate = root / "candidate"
        candidate.mkdir()
        evidence_root = (
            report_path.parent / f"{report_path.stem}-evidence"
            if report_path
            else root / "evidence"
        )
        prompt = _generation_prompt(candidate, result.witness)
        _attempts(
            result,
            candidate,
            prompt,
            executable,
            timeout_sec,
            max_attempts,
            oracle,
            max_budget_usd,
            evidence_root,
        )
        if result.timed_out or any(not item.control_complete for item in result.generation):
            workspace.preserve = True
            result.retained_workspace = str(root)
            result.execution_control = "incomplete_candidate_preserved"
    result.duration_sec = time.monotonic() - started


def _generation_prompt(candidate: Path, witness: str) -> str:
    contract = (FIXTURES / f"witness-{witness}" / "contract.md").read_text()
    (candidate / "contract.md").write_text(contract)
    return (
        "Implement the attached contract in this isolated workspace. "
        "Write only candidate implementation files. Do not change contract.md, "
        "search for evaluator files, or claim tests/certificates you did not run.\n" + contract
    )


def _attempts(
    result: TrialResult,
    candidate: Path,
    prompt: str,
    executable: str,
    timeout_sec: float,
    max_attempts: int,
    oracle: FrozenOracle,
    max_budget_usd: float,
    evidence_root: Path,
    *,
    only_index: bool = False,
) -> None:
    deadline = time.monotonic() + timeout_sec
    for attempt in range(max_attempts):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result.timed_out = True
            result.reason = "generation_timeout"
            return
        before = candidate_identity(candidate) if only_index else {}
        capture = run_process(
            generation_arguments(
                result.runtime, executable, prompt, max_budget_usd=max_budget_usd / max_attempts
            ),
            candidate,
            remaining,
        )
        result.attempts += 1
        result.generation.append(capture)
        result.timed_out = capture.timed_out
        _observed_metadata(result, capture)
        if not capture.control_complete:
            result.outcome, result.reason = "evidence_incomplete", "execution_control_incomplete"
            result.execution_control = "incomplete_candidate_preserved"
            return
        if capture.exit_code != 0 or capture.timed_out:
            result.outcome = "failure"
            result.reason = "generation_timeout" if capture.timed_out else "runtime_failed"
            return
        if only_index:
            after = candidate_identity(candidate)
            before.pop("index.html", None)
            after.pop("index.html", None)
            if before != after:
                result.outcome, result.reason = "invalid", "prepared_ui_non_index_mutation"
                return
        if _evaluate_attempt(result, candidate, oracle, evidence_root, attempt):
            return
        prompt += "\nRepair the existing candidate against the same frozen inputs. " + result.reason


def _evaluate_attempt(
    result: TrialResult, candidate: Path, oracle: FrozenOracle, evidence_root: Path, attempt: int
) -> bool:
    contract_path = candidate / "contract.md"
    if (
        not contract_path.is_file()
        or contract_path.is_symlink()
        or hashlib.sha256(contract_path.read_bytes()).hexdigest() != oracle.contract_sha256
    ):
        result.outcome, result.reason = "invalid", "candidate_contract_changed"
        return True
    build_manifest, capture_receipt = None, None
    if result.witness == "ui-form":
        from tests.integration.helpers.witness_penflow import capture_penflow

        captured_ui = capture_penflow(candidate, evidence_root)
        build_manifest, capture_receipt = captured_ui.manifest, captured_ui.receipt
        result.penflow_diagnostic = captured_ui.diagnostic
    result.candidate_sha256 = candidate_identity(candidate)
    result.candidate_sources = capture_candidate_sources(candidate)
    result.evaluation = evaluate_candidate(
        oracle, candidate, build_manifest=build_manifest, capture_receipt=capture_receipt
    )
    if result.candidate_sha256 != candidate_identity(candidate):
        result.outcome, result.reason = "invalid", "candidate_changed_during_evaluation"
        return True
    status = result.evaluation.status
    result.reason = result.evaluation.reason
    if status == "pass":
        if oracle.scenario == "unauthorized":
            result.outcome, result.reason = (
                "correct_blocked",
                "expected_unauthorized_request_blocked",
            )
        else:
            result.outcome = "first_attempt_success" if attempt == 0 else "repaired_success"
        return True
    if status == "invalid":
        result.outcome = "invalid"
        return True
    result.outcome = "failure"
    if status == "blocked":
        # These witnesses expect success; missing proof is not a correctly blocked product.
        result.outcome = "evidence_incomplete"
        return True
    return False

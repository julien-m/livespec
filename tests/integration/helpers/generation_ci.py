# @spec(FR-014)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-014
"""Persist selected coverage before attempting bounded native generation in CI."""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict
from pathlib import Path

from tests.integration.helpers.generation_selection import coverage_report, select_generation
from tests.integration.helpers.witness_generation import TrialResult, run_generation_trial
from tests.integration.helpers.witness_pipeline import run_pipeline_trial


def main() -> int:
    """Run declared sample/full coverage; missing capability cannot pass the gate."""
    args, budget = _arguments()
    selection = select_generation(
        ["validator/semantic/"], full=args.mode == "full", runtimes=tuple(args.runtimes)
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "selection.json").write_text(json.dumps(asdict(selection), indent=2) + "\n")
    trials: list[TrialResult] = []
    # Persist initial not-run rows so interruption does not erase missing coverage.
    coverage = coverage_report(selection, trials)
    report = args.output / "coverage.json"
    report.write_text(json.dumps(coverage, indent=2) + "\n")
    if args.capability_unavailable:
        trials = [
            TrialResult(witness, runtime, "not_run", reason="ci_auth_unavailable")
            for runtime in selection.runtimes
            for witness in selection.witnesses
        ]
        report.write_text(json.dumps(coverage_report(selection, trials), indent=2) + "\n")
        return 1 if args.mode == "full" else 0
    per_trial_budget = budget / (len(selection.runtimes) * len(selection.witnesses))
    for runtime in selection.runtimes:
        for witness in selection.witnesses:
            trial = _selected_trial(args, runtime, witness, per_trial_budget)
            trials.append(trial)
            coverage = coverage_report(selection, trials)
            report.write_text(json.dumps(coverage, indent=2) + "\n")
    absent_sample = args.mode == "sample" and all(trial.outcome == "not_run" for trial in trials)
    return 0 if coverage["complete"] or absent_sample else 1


def _selected_trial(
    args: argparse.Namespace,
    runtime: str,
    witness: str,
    per_trial_budget: float,
) -> TrialResult:
    """Run one declared coverage cell or persist its concrete missing capability."""
    trial_path = args.output / f"{runtime}-{witness}.json"
    if runtime in args.unavailable_runtimes:
        trial = TrialResult(witness, runtime, "not_run", reason="ci_auth_unavailable")
        trial_path.write_text(json.dumps(trial.to_dict(), indent=2) + "\n")
    elif witness == "ui-form" and args.prepared_ui_candidate is None:
        trial = TrialResult(witness, runtime, "not_run", reason="prepared_ui_source_unavailable")
        trial_path.write_text(json.dumps(trial.to_dict(), indent=2) + "\n")
    elif witness == "python-purge":
        trial = run_pipeline_trial(
            runtime,
            timeout_sec=args.timeout,
            report_path=trial_path,
            max_budget_usd=per_trial_budget,
        )
    else:
        trial = run_generation_trial(
            witness,
            runtime,
            timeout_sec=args.timeout,
            report_path=trial_path,
            max_budget_usd=per_trial_budget,
            prepared_ui_candidate=(args.prepared_ui_candidate if witness == "ui-form" else None),
        )
    return trial


def _arguments() -> tuple[argparse.Namespace, float]:
    """Parse and validate the bounded evaluation request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("sample", "full"), required=True)
    parser.add_argument("--runtimes", nargs="+", choices=("claude", "codex"), default=["claude"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--prepared-ui-candidate", type=Path)
    parser.add_argument("--capability-unavailable", action="store_true")
    parser.add_argument(
        "--unavailable-runtimes", nargs="*", choices=("claude", "codex"), default=[]
    )
    args = parser.parse_args()
    budget = float(os.environ.get("LIVESPEC_TEST_BUDGET_USD", "25"))
    if not math.isfinite(budget) or budget <= 0:
        parser.error("LIVESPEC_TEST_BUDGET_USD must be finite and positive")
    return args, budget


if __name__ == "__main__":
    raise SystemExit(main())

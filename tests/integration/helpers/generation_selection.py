# @spec(FR-014)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-014
"""Choose bounded witness coverage and report selected versus actually completed."""

from __future__ import annotations

from dataclasses import dataclass

from tests.integration.helpers.witness_evaluator import WITNESSES
from tests.integration.helpers.witness_generation import TrialResult

CORE_PATHS = (
    "validator/",
    ".agent-sync/skills/spec-",
    "system/",
    "tests/integration/",
)


@dataclass(frozen=True)
class Selection:
    """Explicit coverage request, independent from observed trial outcomes."""

    mode: str
    witnesses: tuple[str, ...]
    runtimes: tuple[str, ...]


def select_generation(
    changed_paths: list[str], *, full: bool = False, runtimes: tuple[str, ...] = ("claude",)
) -> Selection:
    """Core changes sample Python; release/model/runtime changes select all witnesses."""
    if not runtimes or any(runtime not in ("claude", "codex") for runtime in runtimes):
        raise ValueError("Declare supported runtimes explicitly")
    full = full or any(
        path.startswith(
            (
                "validator/llm_provider.py",
                ".codex/",
                ".claude/",
                "tests/integration/helpers/sdk_runner.py",
                "tests/integration/helpers/witness_generation.py",
                "tests/integration/helpers/witness_runtime.py",
                "tests/integration/helpers/witness_pipeline.py",
                "tests/integration/helpers/witness_process.py",
            )
        )
        for path in changed_paths
    )
    if full:
        return Selection("full", WITNESSES, runtimes)
    core = any(path.startswith(CORE_PATHS) for path in changed_paths)
    return Selection("sample" if core else "none", ("python-purge",) if core else (), runtimes)


def coverage_report(selection: Selection, trials: list[TrialResult]) -> dict[str, object]:
    """Never infer missing runtime/witness parity from another completed result."""
    rows: list[dict[str, object]] = []
    for runtime in selection.runtimes:
        for witness in selection.witnesses:
            matches = [row for row in trials if row.runtime == runtime and row.witness == witness]
            trial = matches[0] if len(matches) == 1 else None
            completed = _completed(trial)
            rows.append(
                {
                    "runtime": runtime,
                    "witness": witness,
                    "selected": True,
                    "attempted": bool(trial and trial.attempts),
                    "completed": completed,
                    "outcome": trial.outcome if trial else "not_run",
                    "reason": trial.reason if trial else "missing_or_duplicate_trial",
                    "stage": trial.stage if trial else None,
                }
            )
    return {
        "mode": selection.mode,
        "rows": rows,
        "complete": bool(rows) and all(row["completed"] for row in rows),
    }


def _completed(trial: TrialResult | None) -> bool:
    # The current witnesses all expect success; business blocking is not their oracle.
    if trial is None or trial.outcome not in ("first_attempt_success", "repaired_success"):
        return False
    evaluated = trial.evaluation
    return bool(
        trial.attempts > 0
        and not trial.timed_out
        and len(trial.oracle_sha256) == 64
        and evaluated
        and evaluated.status == "pass"
        and evaluated.behavior_passed
        and evaluated.assertions > 0
        and evaluated.capture
        and evaluated.capture.exit_code == 0
        and not evaluated.capture.timed_out
        and evaluated.capture.control_complete
        and trial.execution_control == "observed_local_processes"
        and (trial.stage != "spec_feature_pipeline" or trial.pipeline_verified)
    )

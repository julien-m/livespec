# @spec(FR-014)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-014
"""Run the actual spec-feature skill, preserving artifacts through external evaluation."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

from tests.integration.helpers.witness_evaluator import (
    FIXTURES,
    FrozenOracle,
    evaluate_candidate,
    freeze_oracle,
)
from tests.integration.helpers.witness_generation import (
    TrialResult,
    generation_arguments,
)
from tests.integration.helpers.witness_process import ProcessCapture, run_process
from tests.integration.helpers.witness_snapshot import (
    _observed_metadata,
    candidate_identity,
    candidate_policy_identity,
    capture_candidate_sources,
    snapshot_environment,
    snapshot_workflow,
    workflow_identity,
)
from tests.integration.helpers.witness_workspace import WitnessWorkspace
from validator.evidence_policy import EVIDENCE_POLICY_VERSION

REPO = Path(__file__).resolve().parents[3]


def prepare_pipeline_workspace(candidate: Path, source: Path = REPO) -> str:
    """Initialize only framework context; the model must produce every feature artifact/code."""
    specs = candidate / ".specs"
    for directory in ("features", "stacks", "testing"):
        (specs / directory).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / ".specs/spec-system.md", specs / "spec-system.md")
    shutil.copytree(source / ".agent-sync/skills", candidate / ".agent-sync/skills")
    shutil.copytree(source / ".agent-sync/skills", candidate / ".agents/skills")
    shutil.copytree(source / "system", candidate / "system")
    contract = (FIXTURES / "witness-python-purge/contract.md").read_text()
    (candidate / "contract.md").write_text(contract)
    (specs / "project.md").write_text(
        "# Purge witness\n\n## Vision\nA local disposable file cleanup CLI.\n"
        "## Users\nA local CLI operator.\n## Constraints\nPython stdlib only. No UI/network.\n"
    )
    (specs / "constitution.md").write_text(
        "# Constitution\n\n## Rules\nUse Python standard library. Keep files under 300 lines.\n"
        "Use unittest for behavior; never change the supplied contract or external oracle.\n"
    )
    (specs / "stacks/_default.md").write_text(
        "# Default Stack\n\n## Stack\nPython >=3.11, argparse, pathlib, unittest.\n"
        "## Rationale\nNo external dependencies for a local CLI.\n"
    )
    (specs / "testing/strategy.md").write_text(
        "# Testing Strategy\n\nRun python3 -m unittest discover -s tests -v.\n"
        "Test timestamp boundary and preservation using temporary files.\n"
    )
    for name in ("roadmap", "changelog"):
        shutil.copyfile(source / f"system/templates/{name}-template.md", specs / f"{name}.md")
    (specs / "README.md").write_text("# Features\n\nNo features yet.\n")
    (specs / "livespec-version").write_text((source / "VERSION").read_text())
    (candidate / "AGENTS.md").write_text(
        "Read .specs/spec-system.md before any action. LiveSpec-first.\n"
        "Read .agents/skills/spec-feature/SKILL.md for the requested skill.\n"
        "User authorizes the full --auto pipeline and independent native child phases.\n"
        "Do not commit, push, stage, modify contract.md, or write outside this candidate.\n"
        f"Use the authoritative CLI {source / 'bin/livespec'} for every LiveSpec command.\n"
        f"Run certifying pytest commands with {sys.executable}; do not substitute another "
        "Python interpreter or invoke validator.cli through a different runtime.\n"
    )
    return contract


def run_pipeline_trial(
    runtime: str,
    *,
    timeout_sec: float = 300,
    report_path: Path | None = None,
    max_budget_usd: float = 5,
) -> TrialResult:
    """Attempt the current production workflow once and record actual achieved phase artifacts."""
    oracle = freeze_oracle("python-purge")
    result = TrialResult("python-purge", runtime, "not_run", stage="spec_feature_pipeline")
    result.oracle_sha256 = oracle.sha256
    executable = shutil.which(runtime)
    payload: dict[str, object] = {}
    if executable is None:
        result.reason = "runtime_unavailable"
    else:
        started = time.monotonic()
        version = run_process([executable, "--version"], REPO, 10)
        result.runtime_version = version.stdout.strip() or None
        _run_pipeline_workspace(result, oracle, executable, timeout_sec, max_budget_usd, payload)
        result.duration_sec = time.monotonic() - started
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        payload.update(result.to_dict())
        report_path.write_text(json.dumps(payload, indent=2) + "\n")
    return result


def _run_pipeline_workspace(
    result: TrialResult,
    oracle: FrozenOracle,
    executable: str,
    timeout_sec: float,
    max_budget_usd: float,
    payload: dict[str, object],
) -> None:
    with WitnessWorkspace(prefix="livespec_pipeline_candidate_") as workspace:
        root = workspace.root
        candidate, snapshot = root / "candidate", root / "workflow"
        candidate.mkdir()
        identity = snapshot_workflow(REPO, snapshot)
        payload["workflow_sha256"] = identity
        environment = snapshot_environment(snapshot)
        contract = prepare_pipeline_workspace(candidate, snapshot)
        candidate_policy = candidate_policy_identity(candidate)
        payload["candidate_policy_sha256"] = candidate_policy
        command, prompt = _pipeline_prompt(result.runtime, contract)
        payload["command"] = command
        capture = run_process(
            generation_arguments(
                result.runtime, executable, prompt, workflow=True, max_budget_usd=max_budget_usd
            ),
            candidate,
            timeout_sec,
            env=environment,
        )
        _evaluate_pipeline_result(
            result, oracle, workspace, identity, environment, candidate_policy, payload, capture
        )


def _evaluate_pipeline_result(
    result: TrialResult,
    oracle: FrozenOracle,
    workspace: WitnessWorkspace,
    identity: dict[str, str],
    environment: dict[str, str],
    candidate_policy: dict[str, str],
    payload: dict[str, object],
    capture: ProcessCapture,
) -> None:
    root = workspace.root
    candidate, snapshot = root / "candidate", root / "workflow"
    result.attempts = 1
    result.generation = [capture]
    result.timed_out = capture.timed_out
    _observed_metadata(result, capture)
    result.candidate_sha256 = candidate_identity(candidate)
    result.candidate_sources = capture_candidate_sources(candidate)
    control_incomplete = capture.timed_out or not capture.control_complete
    if control_incomplete:
        workspace.preserve = True
        result.retained_workspace = str(root)
        result.execution_control = "incomplete_native_children_not_attested"
    else:
        result.evaluation = evaluate_candidate(oracle, candidate)
    payload["candidate_after_evaluation_sha256"] = candidate_identity(candidate)
    payload["feature_artifacts"] = _feature_artifacts(candidate)
    payload["closure"] = False if control_incomplete else _pipeline_closure(candidate, environment)
    result.pipeline_verified = payload["closure"] is True
    _finish(result, identity, snapshot, payload["closure"] is True)
    if control_incomplete:
        result.outcome = "evidence_incomplete"
        result.reason = "execution_control_incomplete"
    elif result.candidate_sha256 != candidate_identity(candidate):
        result.outcome, result.reason = "invalid", "candidate_changed_during_evaluation"
    if candidate_policy != candidate_policy_identity(candidate):
        result.outcome, result.reason = "invalid", "candidate_workflow_inputs_changed"


def _pipeline_prompt(runtime: str, contract: str) -> tuple[str, str]:
    # This exact skill entrypoint is the production pipeline, not a code-only prompt.
    prefix = "$" if runtime == "codex" else "/"
    command = prefix + 'spec-feature "Implement the Python purge CLI from contract.md" --auto'
    prompt = (
        command + "\nRead .agents/skills/spec-feature/SKILL.md and execute its current "
        "workflow, including independent phase agents and proof gates. The authorized "
        "task is the entire pipeline. Never bypass a missing capability; report its exact "
        "phase. The livespec CLI is installed. Contract:\n" + contract
    )
    return command, prompt


def _feature_artifacts(candidate: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for path in (candidate / ".specs/features").rglob("*.md"):
        relative = str(path.relative_to(candidate))
        if path.is_symlink() or not path.resolve().is_relative_to(candidate.resolve()):
            artifacts[relative] = "INVALID: candidate artifact escapes workspace"
        elif path.is_file():
            artifacts[relative] = (
                path.read_text()
                if path.stat().st_size <= 1_000_000
                else ("INCOMPLETE: artifact exceeds capture limit of 1000000 bytes")
            )
    return artifacts


def _finish(result: TrialResult, identity: dict[str, str], snapshot: Path, closure: bool) -> None:
    try:
        current = workflow_identity(snapshot)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result.outcome = "invalid"
        result.reason = f"production_workflow_identity_unreadable:{exc}"
        return
    if identity != current:
        result.outcome, result.reason = "invalid", "production_workflow_changed_during_trial"
    elif result.timed_out:
        result.outcome, result.reason = "failure", "pipeline_timeout"
    elif result.evaluation and result.evaluation.status == "pass":
        if closure and result.generation[0].exit_code == 0:
            result.outcome, result.reason = "first_attempt_success", "pipeline_and_behavior_passed"
        else:
            result.outcome, result.reason = "failure", "pipeline_closure_not_independently_verified"
    else:
        result.outcome, result.reason = "failure", "pipeline_did_not_produce_passing_candidate"


def _pipeline_closure(candidate: Path, environment: dict[str, str]) -> bool:
    features = list((candidate / ".specs/features").glob("*/pipeline.md"))
    executable = shutil.which("livespec", path=environment["PATH"])
    if len(features) != 1 or executable is None:
        return False
    feature = features[0].parent.name
    for path in (candidate / ".specs/.runs").rglob("*.json"):
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or value.get("command") != "spec-feature":
            continue
        if value.get("feature") != feature:
            continue
        if value.get("evidence_policy_version") != EVIDENCE_POLICY_VERSION:
            continue
        checked = run_process(
            [
                executable,
                "verify-output",
                "spec-feature",
                "--run",
                str(path),
                "--feature",
                feature,
                "--json",
            ],
            candidate,
            30,
            env=environment,
        )
        if (
            checked.exit_code == 0
            and not checked.timed_out
            and checked.control_complete
            and _terminal_pipeline(executable, candidate, feature, environment, value)
        ):
            return True
    return False


def _terminal_pipeline(
    executable: str,
    candidate: Path,
    feature: str,
    environment: dict[str, str],
    archive: dict[str, object],
) -> bool:
    """Do not confuse Typer usage exit 2 with successful terminal progression."""
    flags = archive.get("flags", [])
    if not isinstance(flags, list):
        return False
    review_flags = [
        flag
        for flag in flags
        if isinstance(flag, str) and flag.startswith(("--model=", "--review-max-chars="))
    ]
    terminal = run_process(
        [executable, "pipeline", "next", "--feature", feature, *review_flags],
        candidate,
        30,
        env=environment,
    )
    return (
        terminal.exit_code == 2
        and not terminal.stdout.strip()
        and not terminal.stderr.strip()
        and not terminal.timed_out
        and terminal.control_complete
    )

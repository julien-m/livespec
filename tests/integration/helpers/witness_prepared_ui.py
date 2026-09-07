# @spec(FR-012)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-012
"""Generate against an existing authoritative native design without relocating its receipts."""

from __future__ import annotations

import fcntl
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

from tests.integration.helpers.witness_evaluator import freeze_oracle
from tests.integration.helpers.witness_generation import (
    TrialResult,
    _attempts,
    _generation_prompt,
)
from tests.integration.helpers.witness_penflow import _penflow_executable
from tests.integration.helpers.witness_process import run_process

NORMATIVE = (
    "penflow/flow-ui-contract/contract.json",
    "penflow/expected-ui-tree.json",
    "penflow/code-ir.json",
)


def run_prepared_ui_trial(
    candidate: Path,
    runtime: str,
    *,
    timeout_sec: float = 180,
    max_attempts: int = 2,
    report_path: Path,
    max_budget_usd: float = 5,
) -> TrialResult:
    """Use the supplied dedicated consumer in place; preserve it even after failure."""
    if max_attempts not in (1, 2) or timeout_sec <= 0:
        raise ValueError("One initial attempt and at most one repair, with a positive timeout")
    oracle = freeze_oracle("ui-form")
    result = TrialResult(
        "ui-form", runtime, "not_run", oracle_sha256=oracle.sha256, stage="prepared_ui_generation"
    )
    result.retained_workspace = str(candidate)
    evidence = report_path.parent / f"{report_path.stem}-evidence"
    if candidate.is_symlink():
        raise ValueError("Prepared UI candidate must not be a symlink")
    candidate = candidate.resolve()
    lock_root = Path(tempfile.gettempdir()) / "livespec-prepared-ui-locks"
    lock_root.mkdir(exist_ok=True)
    lock_path = lock_root / (hashlib.sha256(str(candidate).encode()).hexdigest() + ".lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            result.reason = "prepared_ui_candidate_busy"
        else:
            _run_locked(
                candidate, runtime, evidence, result, timeout_sec, max_attempts, max_budget_usd
            )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
    return result


def _run_locked(
    candidate: Path,
    runtime: str,
    evidence: Path,
    result: TrialResult,
    timeout_sec: float,
    max_attempts: int,
    max_budget_usd: float,
) -> None:
    started = time.monotonic()
    executable, authority = shutil.which(runtime), _penflow_executable()
    if executable is None or authority is None:
        result.reason = "prepared_ui_runtime_or_authority_unavailable"
        return
    if not candidate.is_dir() or any(path.is_symlink() for path in candidate.rglob("*")):
        result.reason = "prepared_ui_candidate_invalid"
        return
    evidence.mkdir(parents=True, exist_ok=True)
    if evidence.resolve().is_relative_to(candidate):
        raise ValueError("Prepared UI evidence must remain outside the candidate")
    if not _design_authority(candidate, authority, evidence):
        result.outcome, result.reason = "evidence_incomplete", "prepared_ui_design_not_certified"
        return
    frozen = _normative_identity(candidate)
    if (candidate / "index.html").exists():
        shutil.copyfile(candidate / "index.html", evidence / "previous-index.html")
        (candidate / "index.html").unlink()
    prompt = _prepared_prompt(candidate)
    version = run_process([executable, "--version"], candidate, 10)
    result.runtime_version = version.stdout.strip() or None
    _attempts(
        result,
        candidate,
        prompt,
        executable,
        timeout_sec,
        max_attempts,
        freeze_oracle("ui-form"),
        max_budget_usd,
        evidence,
        only_index=True,
    )
    if frozen != _normative_identity(candidate):
        result.outcome, result.reason = "invalid", "prepared_ui_normative_sources_changed"
    result.duration_sec = time.monotonic() - started
    (evidence / "normative-sources.json").write_text(json.dumps(frozen, indent=2) + "\n")


def _prepared_prompt(candidate: Path) -> str:
    return _generation_prompt(candidate, "ui-form") + (
        "\nRead penflow/code-ir.json, penflow/expected-ui-tree.json and "
        "penflow/flow-ui-contract/contract.json. Implement their approved design exactly. "
        "Only write index.html; all existing files including native authority are immutable. "
        "Render actual data-screen, data-state, data-actor and data-action attributes matching "
        "the declared identities. Do not forge reports, receipts, or observations."
    )


def _design_authority(candidate: Path, cli: str, evidence: Path) -> bool:
    run = run_process(
        [
            cli,
            "run",
            "--target",
            str(candidate / "penflow"),
            "--profile",
            "design",
            "--project",
            str(candidate),
            "--json",
        ],
        candidate,
        60,
    )
    checked = run_process(
        [
            cli,
            "validate-report",
            str(candidate / "penflow/run-report.json"),
            "--schema",
            "--required-profile",
            "design",
            "--project",
            str(candidate),
            "--json",
        ],
        candidate,
        60,
    )
    from dataclasses import asdict

    (evidence / "design-authority.json").write_text(
        json.dumps({"run": asdict(run), "validation": asdict(checked)}, indent=2) + "\n"
    )
    return all(
        item.exit_code == 0 and not item.timed_out and item.control_complete
        for item in (run, checked)
    )


def _normative_identity(candidate: Path) -> dict[str, str]:
    return {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest() for name in NORMATIVE}

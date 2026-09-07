# @spec(FR-012)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-012
"""Frozen external oracles for behavior; no model output can declare a PASS."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tests.integration.helpers.witness_process import ProcessCapture, run_process

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ORACLES = Path(__file__).resolve().parent.parent / "oracles"
WITNESSES = ("python-purge", "typescript-api", "ui-form")
ORACLE_NAMES = {
    "python-purge": "purge_oracle.py",
    "typescript-api": "api_oracle.py",
    "ui-form": "ui-oracle.mjs",
}


@dataclass(frozen=True)
class FrozenOracle:
    """Identity captured by evaluator before generation starts."""

    witness: str
    path: Path
    sha256: str
    contract_sha256: str
    dependencies_sha256: tuple[tuple[str, str], ...] = ()
    scenario: str = "full"


@dataclass(frozen=True)
class Evaluation:
    """Behavior and certification remain separate when a capability is absent."""

    status: Literal["pass", "failure", "invalid", "blocked"]
    behavior_passed: bool
    reason: str
    assertions: int = 0
    capture: ProcessCapture | None = None
    authority_capture: ProcessCapture | None = None


def freeze_oracle(witness: str, *, scenario: str = "full") -> FrozenOracle:
    """Freeze the external executable oracle and public contract before generation."""
    if scenario != "full" and (witness != "typescript-api" or scenario != "unauthorized"):
        raise ValueError("Only the API unauthorized scenario declares expected blocking")
    path = ORACLES / ORACLE_NAMES[witness]
    contract = FIXTURES / f"witness-{witness}" / "contract.md"
    dependencies = (
        (("api-server.mjs", _digest(ORACLES / "api-server.mjs")),)
        if witness == "typescript-api"
        else ()
    )
    return FrozenOracle(witness, path, _digest(path), _digest(contract), dependencies, scenario)


def evaluate_candidate(
    oracle: FrozenOracle,
    candidate: Path,
    *,
    timeout_sec: float = 30,
    build_manifest: Path | None = None,
    capture_receipt: Path | None = None,
) -> Evaluation:
    """Evaluate retained candidate bytes with an independently frozen oracle."""
    if not _unchanged(oracle) or not _confined(candidate, oracle.path):
        return Evaluation("invalid", False, "oracle_changed_or_candidate_escape")
    executable = sys.executable if oracle.witness != "ui-form" else shutil.which("node")
    if executable is None:
        return Evaluation("blocked", False, "node_unavailable")
    try:
        argv = [
            executable,
            *(["-I"] if oracle.witness != "ui-form" else []),
            str(oracle.path),
            str(candidate),
            *([oracle.scenario] if oracle.scenario != "full" else []),
        ]
        capture = run_process(argv, candidate, timeout_sec)
    except OSError as exc:
        return Evaluation("blocked", False, f"oracle_unavailable: {exc}")
    if not _unchanged(oracle) or not _confined(candidate, oracle.path):
        return Evaluation("invalid", False, "oracle_changed_or_candidate_escape", capture=capture)
    if not capture.control_complete:
        return Evaluation("blocked", False, "oracle_execution_control_incomplete", capture=capture)
    assertions = _assertion_count(capture)
    if not assertions:
        reason = "oracle_timeout" if capture.timed_out else "behavioral_assertion_failed"
        return Evaluation("failure", False, reason, capture=capture)
    if oracle.witness == "ui-form":
        return _certify_ui(candidate, assertions, capture, build_manifest, capture_receipt)
    return Evaluation("pass", True, "independent_behavior_passed", assertions, capture)


def _certify_ui(
    candidate: Path,
    assertions: int,
    capture: ProcessCapture,
    build_manifest: Path | None,
    capture_receipt: Path | None,
) -> Evaluation:
    if build_manifest is None or not _independent_capture(
        candidate, build_manifest, capture_receipt
    ):
        return Evaluation(
            "blocked", True, "independent_build_manifest_required", assertions, capture
        )
    # Isolated Python prevents generated local modules shadowing the installed authority.
    script = (
        "import json,sys;from pathlib import Path;from dataclasses import asdict;"
        "from validator.penflow_verification import verify_penflow_report,VerificationProfile;"
        "root=Path(sys.argv[1]);s=verify_penflow_report(root,root/'penflow',"
        "VerificationProfile.IMPLEMENTATION,Path(sys.argv[2]));"
        "print(json.dumps(asdict(s)))"
    )
    environment = {
        **os.environ,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
    }
    authority = run_process(
        [sys.executable, "-I", "-c", script, str(candidate), str(build_manifest)],
        candidate,
        40,
        env=environment,
    )
    try:
        status = json.loads(authority.stdout)
    except ValueError:
        status = {}
    if (
        authority.exit_code != 0
        or not authority.control_complete
        or not isinstance(status, dict)
        or status.get("status") != "PASS"
    ):
        reason = (
            status.get("reason", "invalid_response")
            if isinstance(status, dict)
            else "invalid_response"
        )
        return Evaluation(
            "blocked", True, f"penflow_insufficient: {reason}", assertions, capture, authority
        )
    return Evaluation("pass", True, "browser_and_penflow_passed", assertions, capture, authority)


def _assertion_count(capture: ProcessCapture) -> int:
    if capture.exit_code != 0 or capture.timed_out:
        return 0
    try:
        data = json.loads(capture.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return 0
    count = data.get("assertions") if isinstance(data, dict) else None
    return count if type(count) is int and count > 0 and data.get("passed") is True else 0


def _confined(candidate: Path, oracle: Path) -> bool:
    root = candidate.resolve()
    if candidate.is_symlink() or oracle.resolve().is_relative_to(root):
        return False
    return all(not path.is_symlink() for path in candidate.rglob("*"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unchanged(oracle: FrozenOracle) -> bool:
    contract = FIXTURES / f"witness-{oracle.witness}" / "contract.md"
    try:
        return (
            _digest(oracle.path) == oracle.sha256
            and _digest(contract) == oracle.contract_sha256
            and all(
                _digest(ORACLES / name) == digest for name, digest in oracle.dependencies_sha256
            )
        )
    except OSError:
        return False


def _independent_capture(candidate: Path, manifest: Path, receipt: Path | None) -> bool:
    if receipt is None or receipt.resolve().is_relative_to(candidate.resolve()):
        return False
    try:
        value = json.loads(receipt.read_text())
        return (
            isinstance(value, dict)
            and value.get("kind") == "livespec-witness-penflow-capture"
            and value.get("candidate") == str(candidate.resolve())
            and value.get("manifest")
            == {"path": str(manifest.resolve()), "sha256": _digest(manifest)}
            and value.get("source_sha256") == _digest(candidate / "index.html")
        )
    except (OSError, ValueError):
        return False

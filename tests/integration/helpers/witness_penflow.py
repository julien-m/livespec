"""Capture actual UI evidence and attempt the installed cumulative Penflow authority."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tests.integration.helpers.witness_penflow_runtime import convert_runtime
from tests.integration.helpers.witness_process import run_process

REPO = Path(__file__).resolve().parents[3]
ADAPTER = REPO / "tests/integration/fixtures/witness-ui-form/penflow/capture.mjs"


@dataclass(frozen=True)
class PenflowCapture:
    """Actual capture output; a manifest is an input to C51, never its verdict."""

    manifest: Path | None
    diagnostic: str
    artifacts: tuple[Path, ...] = ()
    receipt: Path | None = None


# @spec FR-012: Runtime evidence remains independent of generated UI.
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-012
def capture_penflow(candidate: Path, evidence_root: Path) -> PenflowCapture:
    """Capture after generation; retain external transcripts and protected runner bytes.

    The caller owns candidate and evidence lifetime. Existing design/approved-source
    artifacts are consumed without repair: missing authority remains explicit.
    """
    if candidate.is_symlink() or evidence_root.is_symlink():
        return PenflowCapture(None, "capture_requires_independent_confined_paths")
    candidate, evidence_root = candidate.resolve(), evidence_root.resolve()
    if evidence_root.is_relative_to(candidate) or any(p.is_symlink() for p in candidate.rglob("*")):
        return PenflowCapture(None, "capture_requires_independent_confined_paths")
    evidence_root.mkdir(parents=True, exist_ok=True)
    node, penflow = shutil.which("node"), _penflow_executable()
    if node is None:
        return PenflowCapture(None, "node_unavailable")
    run_id = uuid4().hex
    runner = candidate / ".witness-runner" / run_id
    runner.mkdir(parents=True)
    adapter = runner / "capture.mjs"
    shutil.copyfile(ADAPTER, adapter)
    raw = runner / "browser.json"
    if not (candidate / "index.html").is_file():
        return _result(None, "candidate_entrypoint_missing", evidence_root)
    source_hash = _digest(candidate / "index.html")
    argv = [node, str(adapter), str(candidate), str(raw), str(REPO / "package.json")]
    browser = _execute(argv, candidate, evidence_root / "browser-process.json")
    if browser != 0 or not raw.is_file():
        return _result(None, "browser_capture_failed", evidence_root)
    shutil.copyfile(raw, evidence_root / "browser.json")
    if source_hash != _digest(candidate / "index.html"):
        return _result(None, "candidate_changed_during_capture", evidence_root)
    if penflow is None:
        return _result(None, "penflow_unavailable", evidence_root)
    return _verify(candidate, evidence_root, runner, source_hash, penflow)


def _verify(
    candidate: Path, evidence: Path, runner: Path, source_hash: str, cli: str
) -> PenflowCapture:
    sources = evidence / "source-authority.json"
    # The installed snapshot API selects authority; filenames never imply approval.
    script = (
        "import json,sys; from penflow.verification_snapshot import verification_source_references;"
        "print(json.dumps(verification_source_references(project_root=sys.argv[1],"
        " workspace=sys.argv[2])))"
    )
    source_exit = _execute(
        [sys.executable, "-I", "-c", script, str(candidate), str(candidate / "penflow")],
        candidate,
        sources,
    )
    manifest = None
    if source_exit == 0:
        references = json.loads(json.loads(sources.read_text())["stdout"])
        try:
            manifest = _manifest(candidate, runner, references)
        except (ValueError, KeyError, StopIteration) as exc:
            _write(evidence / "runtime-conversion.json", {"error": str(exc)})
            return _result(None, "runtime_capture_mapping_invalid", evidence)
    args = [cli, "run", "--target", str(candidate / "penflow"), "--profile", "implementation"]
    if manifest:
        args.extend(["--build-manifest", str(manifest)])
    args.extend(["--project", str(candidate), "--json"])
    _execute(args, candidate, evidence / "penflow-run.json")
    validation = [
        cli,
        "validate-report",
        str(candidate / "penflow/run-report.json"),
        "--schema",
        "--required-profile",
        "implementation",
        "--project",
        str(candidate),
    ]
    if manifest:
        validation.extend(["--build-manifest", str(manifest)])
    validation.append("--json")
    _execute(validation, candidate, evidence / "penflow-validation.json")
    diagnostic = "penflow_authority_evaluated" if manifest else _contract_gap(candidate, evidence)
    receipt = _capture_receipt(candidate, evidence, manifest, source_hash)
    return _result(manifest, diagnostic, evidence, receipt)


def _capture_receipt(
    candidate: Path,
    evidence: Path,
    manifest: Path | None,
    source_hash: str,
) -> Path | None:
    """Bind independently captured candidate bytes to the actual manifest."""
    receipt = None
    if manifest:
        receipt = evidence / "capture-receipt.json"
        _write(
            receipt,
            {
                "kind": "livespec-witness-penflow-capture",
                "candidate": str(candidate),
                "manifest": _reference(manifest),
                "source_sha256": source_hash,
            },
        )
    return receipt


def _manifest(candidate: Path, runner: Path, sources: list[dict[str, str]]) -> Path:
    raw = runner / "browser.json"
    data = json.loads(raw.read_text())
    manifest = runner / "build-manifest.json"
    build_id = uuid4().hex
    runtime_paths = convert_runtime(candidate, runner, build_id)
    _write(
        manifest,
        {
            "kind": "penflow-build-manifest",
            "version": 1,
            "scope": {"project_root": str(candidate)},
            "build": {"id": build_id, "artifacts": [_reference(candidate / "index.html")]},
            "producer": {
                "id": "livespec-witness-browser",
                "entrypoint": _reference(runner / "capture.mjs"),
                "invocation_id": runner.name,
            },
            "capture": {"session_ids": [data["session_id"]], "scenario_ids": [data["scenario_id"]]},
            "sources": sources,
            "evidence": [_reference(path) for path in [raw, *runtime_paths]],
            "issued_at": datetime.now(UTC).isoformat(),
        },
    )
    return manifest


def _execute(argv: list[str], candidate: Path, output: Path) -> int:
    try:
        result = run_process(argv, candidate, 45)
    except OSError as exc:
        _write(output, {"argv": argv, "exit_code": 127, "stdout": "", "stderr": str(exc)})
        return 127
    _write(output, {"argv": argv, **asdict(result)})
    return result.exit_code


def _contract_gap(candidate: Path, evidence: Path) -> str:
    """Probe exact source semantics rather than inventing network duties for a local form."""
    contract = ADAPTER.parent / "form-contract.json"
    shutil.copyfile(contract, evidence / "proposed-flow-contract.json")
    script = (
        "import json,sys; from penflow.flow_contract import validate_flow_contract_v2;"
        "issues=validate_flow_contract_v2(json.load(open(sys.argv[1])));"
        "print(json.dumps(issues));sys.exit(bool(issues))"
    )
    transcript = evidence / "local-submit-capability.json"
    _execute([sys.executable, "-I", "-c", script, str(contract)], candidate, transcript)
    try:
        issues = json.loads(json.loads(transcript.read_text())["stdout"])
    except (json.JSONDecodeError, KeyError):
        return "penflow_source_authority_unavailable"
    if isinstance(issues, list) and any(
        issue.get("code") == "contract.schema.required" and "'mutation'" in issue.get("message", "")
        for issue in issues
        if isinstance(issue, dict)
    ):
        return "penflow_local_submit_requires_unsupported_request_semantics"
    return "penflow_source_authority_unavailable"


def _result(
    manifest: Path | None, reason: str, evidence: Path, receipt: Path | None = None
) -> PenflowCapture:
    _write(evidence / "diagnostic.json", {"diagnostic": reason, "certified": False})
    return PenflowCapture(manifest, reason, tuple(sorted(evidence.iterdir())), receipt)


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _penflow_executable() -> str | None:
    executable = shutil.which("penflow")
    if executable:
        return executable
    sibling = Path(sys.executable).parent / "penflow"
    return str(sibling) if sibling.is_file() and os.access(sibling, os.X_OK) else None


def _reference(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": _digest(path)}

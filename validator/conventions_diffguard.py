"""Supervisor locks for conventions gate files."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .conventions_gate import GateResult
from .conventions_gates import gates_path, load_conventions_gates
from .conventions_rules import rulebook_path
from .visual_evidence import sha256_file


@dataclass(frozen=True)
class BaseHashSnapshot:
    """Conventions gate hashes recorded on the base branch."""

    gates_sha256: str
    rules_sha256: str


@dataclass(frozen=True)
class FreshGateResult:
    """Supervisor conventions gate result based on a fresh local run."""

    verdict: str
    source: str
    stale_worker_verdict: str | None


def changed_protected_conventions_paths(
    project_root: Path,
    *,
    changed_paths: Iterable[str],
) -> list[str]:
    """Return changed paths that are protected conventions gate inputs."""
    protected = _protected_conventions_paths(project_root)
    return sorted(path for path in changed_paths if path in protected)


def git_changed_paths(project_root: Path, *, base_ref: str, head_ref: str) -> list[str]:
    """Return paths changed between two git refs for supervisor diff checks."""
    output = subprocess.check_output(
        ["git", "-C", str(project_root), "diff", "--name-only", f"{base_ref}..{head_ref}"],
        stderr=subprocess.STDOUT,
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def base_hash_snapshot(project_root: Path, *, base_ref: str) -> BaseHashSnapshot:
    """Read protected conventions file hashes from a git base ref."""
    return BaseHashSnapshot(
        gates_sha256=_git_blob_sha256(project_root, base_ref, ".specs/conventions-gates.yaml"),
        rules_sha256=_git_blob_sha256(project_root, base_ref, ".specs/conventions-rulebook.yaml"),
    )


def compare_base_hashes(project_root: Path, snapshot: BaseHashSnapshot) -> list[str]:
    """Return blocker codes for gates/rules hash mismatches vs base branch."""
    blockers: list[str] = []
    if _sha256_or_empty(gates_path(project_root)) != snapshot.gates_sha256:
        blockers.append("gates_sha256_mismatch")
    if _sha256_or_empty(rulebook_path(project_root)) != snapshot.rules_sha256:
        blockers.append("rules_sha256_mismatch")
    return blockers


def supervisor_conventions_gate(
    project_root: Path,
    *,
    worker_receipt: dict[str, object] | None,
    run_verify: Callable[[Path], GateResult],
) -> FreshGateResult:
    """Run conventions verification freshly and ignore stale worker verdicts."""
    fresh = run_verify(project_root)
    stale = None
    if isinstance(worker_receipt, dict) and isinstance(worker_receipt.get("verdict"), str):
        stale = str(worker_receipt["verdict"])
    return FreshGateResult(
        verdict=fresh.verdict.value,
        source="fresh_supervisor_run",
        stale_worker_verdict=stale,
    )


def _protected_conventions_paths(project_root: Path) -> set[str]:
    protected = {
        ".specs/conventions-gates.yaml",
        ".specs/conventions-rulebook.yaml",
    }
    try:
        gates = load_conventions_gates(gates_path(project_root))
    except (OSError, ValueError):
        return protected
    for command in gates.commands.lint + gates.commands.format + gates.commands.typecheck:
        if command.config:
            protected.add(command.config)
    return protected


def _sha256_or_empty(path: Path) -> str:
    try:
        return sha256_file(path)
    except OSError:
        return ""


def _git_blob_sha256(project_root: Path, ref: str, rel_path: str) -> str:
    try:
        content = subprocess.check_output(
            ["git", "-C", str(project_root), "show", f"{ref}:{rel_path}"],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError:
        return ""
    return sha256(content).hexdigest()


__all__ = [
    "BaseHashSnapshot",
    "FreshGateResult",
    "base_hash_snapshot",
    "changed_protected_conventions_paths",
    "compare_base_hashes",
    "git_changed_paths",
    "supervisor_conventions_gate",
]

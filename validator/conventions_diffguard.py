"""Supervisor locks for conventions gate files."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
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


__all__ = [
    "BaseHashSnapshot",
    "FreshGateResult",
    "changed_protected_conventions_paths",
    "compare_base_hashes",
    "supervisor_conventions_gate",
]

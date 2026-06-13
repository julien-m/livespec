"""R7 coherence rules for conventions gates and rulebooks."""

from __future__ import annotations

import fnmatch
import re
from hashlib import sha256
from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation
from validator.conventions_gates import gates_path, load_conventions_gates
from validator.conventions_rules import load_conventions_rules, rulebook_path
from validator.visual_evidence import sha256_file

_CONSTITUTION_SIGNALS = ("conventions", "lint", "linter", "max file", "function lines", "ruff")
_STANDARD_TOOLING_EXCLUSIONS = {
    ".git/**",
    ".ruff_cache/**",
    ".specs/**",
    ".venv/**",
    "**/__pycache__/**",
    "**/Generated/**",
}


class R7_1_ConventionsGatesMissingOrStale:
    """Constitution conventions declarations require fresh gates."""

    rule_id = "R7.1"
    description = "Conventions gates exist and match constitution hash"
    wave = 7

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Return ERROR when gates are missing or stale."""
        constitution = specs_root / "constitution.md"
        if not _constitution_declares_conventions(constitution):
            return []
        gates = gates_path(specs_root.parent)
        if not gates.is_file():
            return [
                _violation(
                    self.rule_id,
                    "constitution declares conventions but conventions-gates.yaml is absent",
                )
            ]
        try:
            loaded = load_conventions_gates(gates)
        except (OSError, ValueError) as exc:
            return [_violation(self.rule_id, f"conventions-gates.yaml invalid: {exc}")]
        source = specs_root.parent / loaded.generated_from.constitution
        if not source.is_file() or sha256_file(source) != loaded.generated_from.constitution_sha256:
            return [_violation(self.rule_id, "conventions gates constitution_sha256 is stale")]
        return []


class R7_2_ConventionsExclusionTooBroad:
    """Conventions exclusions may not hide most of the repository."""

    rule_id = "R7.2"
    description = "Conventions exclusions cover at most 30 percent of repo files"
    wave = 7

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Return ERROR for any exclusion pattern matching more than 30%."""
        try:
            gates = load_conventions_gates(gates_path(specs_root.parent))
        except (OSError, ValueError):
            return []
        files = _repo_files(specs_root.parent)
        if not files:
            return []
        violations: list[Violation] = []
        for pattern in gates.exclusions:
            if pattern in _STANDARD_TOOLING_EXCLUSIONS:
                continue
            matched = [path for path in files if fnmatch.fnmatch(path, pattern)]
            if len(matched) / len(files) > 0.30:
                violations.append(
                    _violation(self.rule_id, f"conventions exclusion {pattern} covers >30% of repo")
                )
        return violations


class R7_3_ConventionsRulebookSourcesStale:
    """Compiled rulebook source hashes must match ai-ressources."""

    rule_id = "R7.3"
    description = "Conventions rulebook source hashes are fresh"
    wave = 7

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Return ERROR when any recorded source hash is stale."""
        try:
            rulebook = load_conventions_rules(rulebook_path(specs_root.parent))
        except (FileNotFoundError, OSError, ValueError):
            return []
        ai_root = _airesources_root(specs_root.parent / ".conventions" / "index.md")
        violations: list[Violation] = []
        for source in rulebook.sources:
            source_path = _resolve_ai_source(source.path, ai_root)
            current_sha = _sha256_path(source_path) if source_path is not None else None
            if current_sha != source.sha256:
                violations.append(
                    _violation(self.rule_id, f"conventions rulebook source stale: {source.path}")
                )
        return violations


def _constitution_declares_conventions(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    return any(signal in text for signal in _CONSTITUTION_SIGNALS)


def _repo_files(project_root: Path) -> list[str]:
    files: list[str] = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(project_root).as_posix()
        if rel.startswith(".git/"):
            continue
        files.append(rel)
    return files


def _airesources_root(index_path: Path) -> Path | None:
    if not index_path.is_file():
        return None
    match = re.search(r"`?\$AIRESOURCES`?\s*=\s*`([^`]+)`", index_path.read_text(encoding="utf-8"))
    return Path(match.group(1)).expanduser().resolve() if match else None


def _resolve_ai_source(display_path: str, ai_root: Path | None) -> Path | None:
    if ai_root is None or not display_path.startswith("$AIRESOURCES/"):
        return None
    resolved = (ai_root / display_path.removeprefix("$AIRESOURCES/")).resolve()
    try:
        resolved.relative_to(ai_root)
    except ValueError:
        return None
    return resolved


def _sha256_path(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    return sha256(path.read_bytes()).hexdigest()


def _violation(rule_id: str, message: str) -> Violation:
    return Violation(rule_id=rule_id, severity=Severity.ERROR, message=message)

"""Subprocess linter execution for deterministic conventions gates."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from .conventions_feature_scope import FeatureScope
from .conventions_gate_types import GateSeverity, GateViolation
from .conventions_gates import DEFAULT_SOURCE_EXCLUSIONS, ConventionsGatesAny
from .conventions_linter import LinterViolationPayload, parse_linter_json


def collect_linter_violations(
    project_root: Path,
    gates: ConventionsGatesAny,
    feature_scope: FeatureScope | None = None,
) -> list[GateViolation]:
    """Run configured lint commands and normalize their violations."""
    violations: list[GateViolation] = []
    exclusions = (*DEFAULT_SOURCE_EXCLUSIONS, *gates.exclusions)
    for command in gates.commands.lint:
        try:
            # `command.run` comes from trusted gates config. stdout is parsed as
            # linter JSON; exit 1 means findings, other non-zero exits fail the
            # command, and timeout bounds the shell boundary.
            completed = subprocess.run(
                command.run,
                cwd=project_root,
                shell=True,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            message = f"{command.id} timed out after {exc.timeout} seconds"
            violations.append(
                GateViolation("linter_timeout", ".", 1, GateSeverity.ERROR, message, "system")
            )
            continue
        parsed = parse_linter_json(command, completed.stdout)
        violations.extend(
            _parsed_linter_violations(project_root, parsed, exclusions, feature_scope)
        )
        violations.extend(
            _unparsed_linter_failure(command.id, completed.returncode, parsed, completed)
        )
    return violations


def _parsed_linter_violations(
    project_root: Path,
    parsed: list[LinterViolationPayload],
    exclusions: tuple[str, ...],
    feature_scope: FeatureScope | None,
) -> list[GateViolation]:
    violations: list[GateViolation] = []
    for item in parsed:
        rel = _project_relative_path(project_root, item.path)
        if _is_excluded_path(rel, exclusions) or not _is_in_scope(rel, feature_scope):
            continue
        violations.append(
            GateViolation(
                item.rule_id,
                item.path,
                item.line,
                GateSeverity(item.severity),
                item.message,
                "linter",
            )
        )
    return violations


def _unparsed_linter_failure(
    command_id: str,
    returncode: int,
    parsed: list[LinterViolationPayload],
    completed: subprocess.CompletedProcess[str],
) -> list[GateViolation]:
    if returncode == 1 and not parsed:
        message = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"{command_id} reported violations but produced no parseable JSON"
        )
        return [
            GateViolation(f"linter.{command_id}", ".", 1, GateSeverity.ERROR, message, "linter")
        ]
    if returncode not in (0, 1):
        message = completed.stderr.strip() or f"{command_id} failed"
        return [
            GateViolation(f"linter.{command_id}", ".", 1, GateSeverity.ERROR, message, "linter")
        ]
    return []


def _is_in_scope(rel: str, feature_scope: FeatureScope | None) -> bool:
    return feature_scope is None or rel in feature_scope.paths


def _is_excluded_path(rel: str, exclusions: tuple[str, ...]) -> bool:
    return any(_matches_exclusion(rel, pattern) for pattern in exclusions)


def _matches_exclusion(rel: str, pattern: str) -> bool:
    if fnmatch.fnmatch(rel, pattern):
        return True
    if pattern.endswith("/**"):
        base_pattern = pattern[:-3]
        return fnmatch.fnmatch(rel, base_pattern) or fnmatch.fnmatch(rel, f"{base_pattern}/*")
    return False


def _project_relative_path(project_root: Path, path: str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()

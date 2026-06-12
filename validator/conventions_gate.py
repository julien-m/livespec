# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-005)

"""Deterministic conventions verification engine."""

from __future__ import annotations

import fnmatch
import re
import shlex
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.

from .conventions_delegate import is_rule_delegated
from .conventions_gates import ConventionsGates, GateCommand, gates_path, load_conventions_gates
from .conventions_lang import adapter_for_path
from .conventions_lang.base import SourceAnalysis
from .conventions_linter import LinterViolationPayload, parse_linter_json
from .visual_evidence import sha256_file

GateSeverityInput = Literal["warning", "error"]
SourceKind = Literal["builtin", "linter", "system"]


class GateSeverity(StrEnum):
    """Violation severity."""

    WARNING = "warning"
    ERROR = "error"


class GateVerdict(StrEnum):
    """Overall conventions verdict."""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class GateViolation:
    """One convention violation."""

    rule_id: str
    path: str
    line: int
    severity: GateSeverity | GateSeverityInput
    message: str
    source: SourceKind
    fix_hint: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable violation payload."""
        severity = self.severity.value if isinstance(self.severity, GateSeverity) else self.severity
        return {
            "rule_id": self.rule_id,
            "path": self.path,
            "line": self.line,
            "severity": severity,
            "message": self.message,
            "source": self.source,
            "fix_hint": self.fix_hint,
        }


@dataclass(frozen=True)
class GateBlocker:
    """One BLOCKED condition."""

    code: str
    message: str
    fix_hint: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return JSON-serializable blocker payload."""
        return {"code": self.code, "message": self.message, "fix_hint": self.fix_hint}


@dataclass(frozen=True)
class GateResult:
    """Complete conventions verification result."""

    verdict: GateVerdict
    violations: list[GateViolation]
    blockers: list[GateBlocker]

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable result payload."""
        return {
            "verdict": self.verdict.value,
            "violations": [violation.to_dict() for violation in self.violations],
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def verify_conventions(project_root: Path, *, report: bool = False) -> GateResult:
    """Run deterministic conventions verification.

    Args:
        project_root: Project root.
        report: Write debt report artifacts when true.

    Returns:
        Gate result with PASS/FAIL/BLOCKED verdict.
    """
    gates = load_conventions_gates(gates_path(project_root))
    blockers = _command_blockers(project_root, gates)
    violations = [] if blockers else _collect_violations(project_root, gates)
    result = _result_from(violations, blockers)
    if report:
        from .conventions_report import write_debt_report

        write_debt_report(project_root, result)
    return result


def _command_blockers(project_root: Path, gates: ConventionsGates) -> list[GateBlocker]:
    blockers = _staleness_blockers(project_root, gates)
    for command in gates.commands.lint + gates.commands.format + gates.commands.typecheck:
        blockers.extend(_version_blockers(command))
        blockers.extend(_sync_limit_blockers(project_root, gates, command))
    return blockers


def _staleness_blockers(project_root: Path, gates: ConventionsGates) -> list[GateBlocker]:
    constitution = project_root / gates.generated_from.constitution
    if not constitution.is_file():
        return [
            GateBlocker(
                "gates_source_missing",
                f"{gates.generated_from.constitution} not found",
                "Run `livespec conventions gates init --force` after restoring the source.",
            )
        ]
    if sha256_file(constitution) == gates.generated_from.constitution_sha256:
        return []
    return [
        GateBlocker(
            "gates_stale",
            "constitution hash differs from generated_from.constitution_sha256",
            "Run `livespec conventions gates init --force` and review the gates diff.",
        )
    ]


def _version_blockers(command: GateCommand) -> list[GateBlocker]:
    if not command.version:
        return []
    executable = shlex.split(command.run)[0]
    try:
        # External linter contract: declared command must expose `--version`; a
        # mismatch blocks because lint output semantics may differ by version.
        completed = subprocess.run(
            [executable, "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [GateBlocker("tool_unavailable", f"{command.id} unavailable: {exc}")]
    output = completed.stdout.strip()
    if command.version not in output:
        return [
            GateBlocker(
                "version_mismatch",
                f"{command.id} version mismatch: expected {command.version}, got {output}",
            )
        ]
    return []


def _sync_limit_blockers(
    project_root: Path,
    gates: ConventionsGates,
    command: GateCommand,
) -> list[GateBlocker]:
    if command.id != "swiftlint" or not command.config:
        return []
    path = project_root / command.config
    if not path.is_file():
        return []
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [GateBlocker("config_invalid", f"{command.config} invalid: {exc}")]
    if not isinstance(raw, dict):
        return [GateBlocker("config_invalid", f"{command.config} root must be mapping")]
    mismatches = _swiftlint_limit_mismatches(raw, gates)
    if not mismatches:
        return []
    return [
        GateBlocker(
            "config_limit_mismatch",
            f"{command.config} limits differ from conventions gates: {', '.join(mismatches)}",
            "Run `livespec conventions scaffold --apply --sync-limits`.",
        )
    ]


def _collect_violations(project_root: Path, gates: ConventionsGates) -> list[GateViolation]:
    violations: list[GateViolation] = []
    for path in _source_files(project_root, gates):
        text = path.read_text(encoding="utf-8")
        analysis = adapter_for_path(path).analyze(path, text)
        rel = path.relative_to(project_root).as_posix()
        violations.extend(_file_length_violations(rel, text, gates))
        violations.extend(_function_length_violations(rel, analysis, gates))
        violations.extend(_file_header_violations(rel, text, analysis, gates))
        violations.extend(_doc_coverage_violations(rel, analysis, gates))
        violations.extend(_token_scale_violations(rel, analysis, gates))
        violations.extend(_suppression_violations(rel, analysis, gates))
        violations.extend(_import_rule_violations(rel, analysis, gates))
    violations.extend(_linter_violations(project_root, gates))
    return violations


def _source_files(project_root: Path, gates: ConventionsGates) -> list[Path]:
    suffixes = {".py", ".ts", ".tsx", ".js", ".jsx", ".swift", ".css"}
    files: list[Path] = []
    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        rel = path.relative_to(project_root).as_posix()
        if any(fnmatch.fnmatch(rel, pattern) for pattern in gates.exclusions):
            continue
        files.append(path)
    return files


def _file_length_violations(rel: str, text: str, gates: ConventionsGates) -> list[GateViolation]:
    count = len(text.splitlines())
    rule = gates.builtin.max_file_lines
    if is_rule_delegated(gates.commands, rule.delegate_to, "builtin.max_file_lines"):
        return []
    if count > rule.limit:
        return [
            _violation("builtin.max_file_lines", rel, 1, "error", f"{count} lines > {rule.limit}")
        ]
    if count > rule.target:
        return [
            _violation(
                "builtin.max_file_lines", rel, 1, "warning", f"{count} lines > {rule.target}"
            )
        ]
    return []


def _function_length_violations(
    rel: str,
    analysis: SourceAnalysis,
    gates: ConventionsGates,
) -> list[GateViolation]:
    rule = gates.builtin.max_function_lines
    if is_rule_delegated(gates.commands, rule.delegate_to, "builtin.max_function_lines"):
        return []
    violations: list[GateViolation] = []
    for function in analysis.functions:
        if function.line_count > rule.limit:
            violations.append(
                _violation(
                    "builtin.max_function_lines",
                    rel,
                    function.start_line,
                    "error",
                    f"{function.name} has {function.line_count} lines > {rule.limit}",
                )
            )
        elif function.line_count > rule.target:
            violations.append(
                _violation(
                    "builtin.max_function_lines",
                    rel,
                    function.start_line,
                    "warning",
                    f"{function.name} has {function.line_count} lines > {rule.target}",
                )
            )
    return violations


def _file_header_violations(
    rel: str,
    text: str,
    analysis: SourceAnalysis,
    gates: ConventionsGates,
) -> list[GateViolation]:
    pattern = gates.builtin.file_header.get(analysis.language)
    if not pattern or re.search(pattern, text):
        return []
    return [_violation("builtin.file_header", rel, 1, "error", "missing required file header")]


def _doc_coverage_violations(
    rel: str,
    analysis: SourceAnalysis,
    gates: ConventionsGates,
) -> list[GateViolation]:
    if not gates.builtin.doc_coverage.get("require_public_api", False):
        return []
    return [
        _violation(
            "builtin.doc_coverage", rel, function.start_line, "warning", "public API lacks docs"
        )
        for function in analysis.functions
        if function.is_public and not function.has_doc
    ]


def _token_scale_violations(
    rel: str,
    analysis: SourceAnalysis,
    gates: ConventionsGates,
) -> list[GateViolation]:
    scale = set(gates.builtin.token_scale.scale)
    properties = set(gates.builtin.token_scale.properties)
    return [
        _violation(
            "builtin.token_scale",
            rel,
            token.line,
            "error",
            f"{token.property_name} uses {token.value}, outside token scale",
        )
        for token in analysis.token_usages
        if token.property_name in properties and token.value not in scale
    ]


def _suppression_violations(
    rel: str,
    analysis: SourceAnalysis,
    gates: ConventionsGates,
) -> list[GateViolation]:
    allowed = set(gates.builtin.suppression_directives.whitelist)
    budget = gates.builtin.suppression_directives.budget
    counted = [item for item in analysis.suppressions if rel not in allowed]
    if len(counted) <= budget:
        return []
    return [
        _violation(
            "builtin.suppression_directives",
            rel,
            item.line,
            "error",
            f"suppression directive `{item.token}` exceeds budget {budget}",
        )
        for item in counted
    ]


def _import_rule_violations(
    rel: str,
    analysis: SourceAnalysis,
    gates: ConventionsGates,
) -> list[GateViolation]:
    violations: list[GateViolation] = []
    for rule in gates.builtin.import_rules:
        forbid = rule.get("forbid", {})
        from_pattern = forbid.get("from", "")
        import_pattern = forbid.get("import", "")
        if not fnmatch.fnmatch(rel, from_pattern):
            continue
        violations.extend(
            _violation(
                "builtin.import_rules", rel, ref.line, "error", f"forbidden import {ref.module}"
            )
            for ref in analysis.imports
            if _matches_import(rel, ref.module, import_pattern)
        )
    return violations


def _linter_violations(project_root: Path, gates: ConventionsGates) -> list[GateViolation]:
    violations: list[GateViolation] = []
    for command in gates.commands.lint:
        completed = subprocess.run(
            command.run,
            cwd=project_root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        parsed = parse_linter_json(command, completed.stdout)
        violations.extend(_linter_payload_to_violation(item) for item in parsed)
        if completed.returncode == 1 and not parsed:
            violations.append(
                GateViolation(
                    f"linter.{command.id}",
                    ".",
                    1,
                    GateSeverity.ERROR,
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or f"{command.id} reported violations but produced no parseable JSON",
                    "linter",
                )
            )
        elif completed.returncode not in (0, 1):
            violations.append(
                GateViolation(
                    f"linter.{command.id}",
                    ".",
                    1,
                    GateSeverity.ERROR,
                    completed.stderr.strip() or f"{command.id} failed",
                    "linter",
                )
            )
    return violations


def _linter_payload_to_violation(payload: LinterViolationPayload) -> GateViolation:
    return _violation(
        payload.rule_id, payload.path, payload.line, payload.severity, payload.message, "linter"
    )


def _result_from(violations: list[GateViolation], blockers: list[GateBlocker]) -> GateResult:
    if blockers:
        return GateResult(GateVerdict.BLOCKED, violations, blockers)
    has_errors = any(
        (v.severity.value if isinstance(v.severity, GateSeverity) else v.severity) == "error"
        for v in violations
    )
    return GateResult(GateVerdict.FAIL if has_errors else GateVerdict.PASS, violations, blockers)


def _swiftlint_limit_mismatches(raw: dict[str, object], gates: ConventionsGates) -> list[str]:
    return [
        *_threshold_mismatches(raw, "file_length", gates.builtin.max_file_lines),
        *_threshold_mismatches(raw, "function_body_length", gates.builtin.max_function_lines),
    ]


def _threshold_mismatches(raw: dict[str, object], key: str, rule: object) -> list[str]:
    values = raw.get(key)
    if not isinstance(values, dict):
        return []
    threshold = cast(Any, rule)
    mismatches: list[str] = []
    if values.get("warning") != threshold.target:
        mismatches.append(f"{key}.warning")
    if values.get("error") != threshold.limit:
        mismatches.append(f"{key}.error")
    return mismatches


def _matches_import(rel: str, module: str, import_pattern: str) -> bool:
    normalized = module.replace("../", "").replace("./", "")
    if fnmatch.fnmatch(normalized, import_pattern):
        return True
    if import_pattern.endswith("/**"):
        expected = import_pattern[:-3].split("/")[-1]
        return expected in normalized or expected in rel
    return False


def _violation(
    rule_id: str,
    path: str,
    line: int,
    severity: GateSeverityInput,
    message: str,
    source: SourceKind = "builtin",
) -> GateViolation:
    return GateViolation(rule_id, path, line, GateSeverity(severity), message, source)

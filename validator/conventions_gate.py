# @spec(FR-006)

# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-005)

"""Deterministic conventions verification engine."""

from __future__ import annotations

import fnmatch
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, cast

import yaml

from .conventions_ast.engine import run_ast_conventions
from .conventions_feature_scope import SOURCE_SUFFIXES, FeatureScope
from .conventions_gate_types import (
    GateBlocker,
    GateResult,
    GateSeverity,
    GateSeverityInput,
    GateVerdict,
    GateViolation,
    SourceKind,
)
from .conventions_gates import (
    DEFAULT_SOURCE_EXCLUSIONS,
    ConventionsGatesAny,
    ConventionsGatesV2,
    GateCommand,
    gates_path,
    load_conventions_gates,
)
from .conventions_lang import adapter_for_path
from .conventions_lang.base import SourceAnalysis
from .conventions_linter import parse_linter_json
from .visual_evidence import sha256_file

_BLOCKING_VIOLATION_RULES = frozenset({"linter_timeout", "file_encoding_error", "file_read_error"})


def verify_conventions(
    project_root: Path,
    *,
    report: bool = False,
    feature_scope: FeatureScope | None = None,
) -> GateResult:
    """Run deterministic conventions verification for a project root."""
    gates = load_conventions_gates(gates_path(project_root))
    blockers = _command_blockers(project_root, gates)
    ast_summary: dict[str, object] | None = None
    if blockers:
        violations: list[GateViolation] = []
    else:
        violations = _collect_violations(project_root, gates, feature_scope)
        if _ast_enabled(gates):
            ast_result = run_ast_conventions(
                project_root,
                gates,
                source_files=_source_files(project_root, gates, feature_scope),
            )
            violations.extend(ast_result.violations)
            blockers.extend(ast_result.blockers)
            ast_summary = ast_result.summary
    result = _result_from(violations, blockers, ast_summary=ast_summary)
    if report:
        from .conventions_report import write_debt_report

        write_debt_report(project_root, result)
    return result


def _command_blockers(project_root: Path, gates: ConventionsGatesAny) -> list[GateBlocker]:
    blockers = _staleness_blockers(project_root, gates)
    for command in gates.commands.lint + gates.commands.format + gates.commands.typecheck:
        blockers.extend(_version_blockers(command))
        blockers.extend(_sync_limit_blockers(project_root, gates, command))
    return blockers


def _staleness_blockers(project_root: Path, gates: ConventionsGatesAny) -> list[GateBlocker]:
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
    gates: ConventionsGatesAny,
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


def _collect_violations(
    project_root: Path,
    gates: ConventionsGatesAny,
    feature_scope: FeatureScope | None,
) -> list[GateViolation]:
    violations: list[GateViolation] = []
    for path in _source_files(project_root, gates, feature_scope):
        rel = path.relative_to(project_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            message = f"{rel} is not valid UTF-8: {exc.reason}"
            violations.append(_system_error("file_encoding_error", rel, message))
            continue
        except (PermissionError, OSError) as exc:
            message = f"{rel} could not be read: {exc}"
            violations.append(_system_error("file_read_error", rel, message))
            continue
        analysis = adapter_for_path(path).analyze(path, text)
        violations.extend(_file_length_violations(rel, text, gates))
        violations.extend(_function_length_violations(rel, analysis, gates))
        violations.extend(_file_header_violations(rel, text, analysis, gates))
        violations.extend(_doc_coverage_violations(rel, analysis, gates))
        violations.extend(_token_scale_violations(rel, analysis, gates))
        violations.extend(_suppression_violations(rel, analysis, gates))
        violations.extend(_import_rule_violations(rel, analysis, gates))
    violations.extend(_linter_violations(project_root, gates, feature_scope))
    return violations


def _source_files(
    project_root: Path,
    gates: ConventionsGatesAny,
    feature_scope: FeatureScope | None = None,
) -> list[Path]:
    files: list[Path] = []
    exclusions = _effective_exclusions(gates)
    for root, dirnames, filenames in os.walk(project_root):
        root_path = Path(root)
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if not _is_excluded_path((root_path / dirname).relative_to(project_root), exclusions)
        )
        for filename in sorted(filenames):
            path = root_path / filename
            if path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            rel = path.relative_to(project_root)
            if _is_excluded_path(rel, exclusions):
                continue
            if not _is_in_scope(rel.as_posix(), feature_scope):
                continue
            files.append(path)
    return files


def _is_in_scope(rel: str, feature_scope: FeatureScope | None) -> bool:
    return feature_scope is None or rel in feature_scope.paths


def _effective_exclusions(gates: ConventionsGatesAny) -> tuple[str, ...]:
    return (*DEFAULT_SOURCE_EXCLUSIONS, *gates.exclusions)


def _is_excluded_path(path: Path | str, exclusions: tuple[str, ...]) -> bool:
    rel = path.as_posix() if isinstance(path, Path) else path
    return any(_matches_exclusion(rel, pattern) for pattern in exclusions)


def _project_relative_path(project_root: Path, path: str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _matches_exclusion(rel: str, pattern: str) -> bool:
    if fnmatch.fnmatch(rel, pattern):
        return True
    if pattern.endswith("/**"):
        base_pattern = pattern[:-3]
        return fnmatch.fnmatch(rel, base_pattern) or fnmatch.fnmatch(rel, f"{base_pattern}/*")
    return False


def _file_length_violations(
    rel: str,
    text: str,
    gates: ConventionsGatesAny,
) -> list[GateViolation]:
    count = len(text.splitlines())
    rule = gates.builtin.max_file_lines
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
    gates: ConventionsGatesAny,
) -> list[GateViolation]:
    rule = gates.builtin.max_function_lines
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
    gates: ConventionsGatesAny,
) -> list[GateViolation]:
    pattern = gates.builtin.file_header.get(analysis.language)
    if not pattern or re.search(pattern, text):
        return []
    return [_violation("builtin.file_header", rel, 1, "error", "missing required file header")]


def _doc_coverage_violations(
    rel: str,
    analysis: SourceAnalysis,
    gates: ConventionsGatesAny,
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
    gates: ConventionsGatesAny,
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
    gates: ConventionsGatesAny,
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
    gates: ConventionsGatesAny,
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


def _linter_violations(
    project_root: Path,
    gates: ConventionsGatesAny,
    feature_scope: FeatureScope | None = None,
) -> list[GateViolation]:
    violations: list[GateViolation] = []
    exclusions = _effective_exclusions(gates)
    for command in gates.commands.lint:
        try:
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
            _violation(item.rule_id, item.path, item.line, item.severity, item.message, "linter")
            for item in parsed
            if not _is_excluded_path(_project_relative_path(project_root, item.path), exclusions)
            and _is_in_scope(_project_relative_path(project_root, item.path), feature_scope)
        )
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


def _ast_enabled(gates: ConventionsGatesAny) -> bool:
    return isinstance(gates, ConventionsGatesV2) and gates.ast_rules.mode != "off"


def _result_from(
    violations: list[GateViolation],
    blockers: list[GateBlocker],
    *,
    ast_summary: dict[str, object] | None = None,
) -> GateResult:
    if blockers:
        return GateResult(GateVerdict.BLOCKED, violations, blockers, ast_summary=ast_summary)
    blocking_violations = [
        violation for violation in violations if violation.rule_id in _BLOCKING_VIOLATION_RULES
    ]
    if blocking_violations:
        blockers = [
            GateBlocker(violation.rule_id, violation.message, violation.fix_hint)
            for violation in blocking_violations
        ]
        return GateResult(GateVerdict.BLOCKED, violations, blockers, ast_summary=ast_summary)
    has_errors = any(
        (v.severity.value if isinstance(v.severity, GateSeverity) else v.severity) == "error"
        for v in violations
    )
    return GateResult(
        GateVerdict.FAIL if has_errors else GateVerdict.PASS,
        violations,
        blockers,
        ast_summary=ast_summary,
    )


def _swiftlint_limit_mismatches(raw: dict[str, object], gates: ConventionsGatesAny) -> list[str]:
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


def _system_error(rule_id: str, path: str, message: str) -> GateViolation:
    return GateViolation(rule_id, path, 1, GateSeverity.ERROR, message, "system")

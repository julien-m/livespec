# @spec FR-001: LiveSpec authority — .specs/features/072-conventions-ast-rule-engine/spec.md#fr-001

"""AST conventions mode dispatcher and LiveSpec gate conversion."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from validator.conventions_ast.backends.ast_grep import AstGrepBackend
from validator.conventions_ast.backends.base import AstBackend
from validator.conventions_ast.catalog import (
    AstCatalogError,
    ast_catalogs_sha256,
    load_ast_catalogs,
)
from validator.conventions_ast.models import (
    AstBackendInfo,
    AstEngineResult,
    AstMatch,
    AstRule,
    AstSourceFile,
)
from validator.conventions_gate_types import GateBlocker, GateSeverity, GateViolation
from validator.conventions_gates import AstRulesConfig, ConventionsGatesAny, ConventionsGatesV2
from validator.conventions_lang import adapter_for_path


# @spec FR-006: AST off mode no-op — .specs/features/072-conventions-ast-rule-engine/spec.md#fr-006
# @spec FR-007: AST observe mode — .specs/features/072-conventions-ast-rule-engine/spec.md#fr-007
# @spec FR-008: AST enforce mode — .specs/features/072-conventions-ast-rule-engine/spec.md#fr-008
def run_ast_conventions(
    project_root: Path,
    gates: ConventionsGatesAny,
    *,
    source_files: Sequence[Path],
    backend: AstBackend | None = None,
) -> AstEngineResult:
    """Run AST conventions according to the gates rollout mode."""
    ast_rules = _ast_rules_config(gates)
    if ast_rules is None or ast_rules.mode == "off":
        return AstEngineResult(summary=None, violations=[], blockers=[])
    try:
        catalogs = load_ast_catalogs(ast_rules.catalogs, project_root=project_root)
    except AstCatalogError as exc:
        return _catalog_error_result(ast_rules.mode, ast_rules, str(exc))
    rules = tuple(rule for catalog in catalogs for rule in catalog.rules)
    backend_result = (backend or _backend_from_config(ast_rules)).scan(
        rules=rules,
        source_files=tuple(_source_metadata(source_files)),
    )
    active_matches = tuple(
        match for match in backend_result.matches if not _is_justified_match(match, rules)
    )
    observations = [_observation(project_root, match, rules) for match in active_matches]
    summary: dict[str, object] = {
        "ast_mode": ast_rules.mode,
        "ast_backend": backend_result.info.to_dict(),
        "ast_catalogs_sha256": ast_catalogs_sha256(catalogs),
        "ast_observations": observations,
        "ast_would_fail_count": len(observations),
    }
    if backend_result.info.status in {"unavailable", "error"}:
        if ast_rules.mode == "enforce":
            return AstEngineResult(
                summary=summary,
                violations=[],
                blockers=[_backend_blocker(backend_result.info)],
            )
        return AstEngineResult(summary=summary, violations=[], blockers=[])
    if ast_rules.mode == "observe":
        return AstEngineResult(summary=summary, violations=[], blockers=[])
    return AstEngineResult(
        summary=summary,
        violations=[_violation(project_root, match, rules) for match in active_matches],
        blockers=[],
    )


def _ast_rules_config(gates: ConventionsGatesAny) -> AstRulesConfig | None:
    if isinstance(gates, ConventionsGatesV2):
        return gates.ast_rules
    return None


def _backend_from_config(ast_rules: AstRulesConfig) -> AstBackend:
    return AstGrepBackend(
        command=ast_rules.backend.command,
        timeout_seconds=ast_rules.backend.timeout_seconds,
    )


def _source_metadata(source_files: Sequence[Path]) -> list[AstSourceFile]:
    metadata: list[AstSourceFile] = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        analysis = adapter_for_path(path).analyze(path, text)
        metadata.append(AstSourceFile(path=path, language=analysis.language, text=text))
    return metadata


def _catalog_error_result(
    mode: str,
    ast_rules: AstRulesConfig,
    message: str,
) -> AstEngineResult:
    info = AstBackendInfo(
        name=ast_rules.backend.name,
        command=ast_rules.backend.command,
        status="error",
        message=message,
    )
    summary: dict[str, object] = {
        "ast_mode": mode,
        "ast_backend": info.to_dict(),
        "ast_catalogs_sha256": "0" * 64,
        "ast_observations": [],
        "ast_would_fail_count": 0,
    }
    if mode == "enforce":
        return AstEngineResult(
            summary=summary,
            violations=[],
            blockers=[GateBlocker("ast_catalog_invalid", message)],
        )
    return AstEngineResult(summary=summary, violations=[], blockers=[])


def _backend_blocker(info: AstBackendInfo) -> GateBlocker:
    code = "ast_backend_unavailable" if info.status == "unavailable" else "ast_backend_error"
    message = info.message or f"{info.name} backend {info.status}"
    return GateBlocker(code, message, "Install ast-grep or switch ast_rules.mode to observe/off.")


def _rule_for_match(match: AstMatch, rules: tuple[AstRule, ...]) -> AstRule:
    for rule in rules:
        if rule.id == match.rule_id:
            return rule
    raise ValueError(f"unknown AST rule match: {match.rule_id}")


def _observation(
    project_root: Path,
    match: AstMatch,
    rules: tuple[AstRule, ...],
) -> dict[str, object]:
    rule = _rule_for_match(match, rules)
    return {
        "rule_id": match.rule_id,
        "path": _relative_path(project_root, match.path),
        "line": match.line,
        "severity": rule.severity,
        "message": match.message,
        "source_path": rule.source_path,
        "source_anchor": rule.source_anchor,
    }


def _is_justified_match(match: AstMatch, rules: tuple[AstRule, ...]) -> bool:
    rule = _rule_for_match(match, rules)
    if not rule.justification.required:
        return False
    try:
        lines = match.path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    line_index = max(match.line - 1, 0)
    start = max(line_index - 1, 0)
    end = min(line_index + 2, len(lines))
    for candidate in lines[start:end]:
        if rule.justification.rule_id_required and rule.id not in candidate:
            continue
        if "livespec-justify" in candidate or "justify" in candidate:
            return True
    return False


# @spec FR-009: AST SourceKind — .specs/features/072-conventions-ast-rule-engine/spec.md#fr-009
def _violation(project_root: Path, match: AstMatch, rules: tuple[AstRule, ...]) -> GateViolation:
    rule = _rule_for_match(match, rules)
    return GateViolation(
        rule_id=match.rule_id,
        path=_relative_path(project_root, match.path),
        line=match.line,
        severity=GateSeverity(rule.severity),
        message=match.message,
        source="ast",
        fix_hint=f"See {rule.source_path}{rule.source_anchor}",
    )


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()

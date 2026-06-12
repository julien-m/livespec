# LiveSpec traceability anchors
# @spec FR-005: Finding schema, FR-006: Domain batching, FR-007: Verdicts, FR-008: Provider blocked — .specs/features/062-conventions-rulebook-semantic/spec.md#fr-005  # noqa: E501 - LiveSpec anchor paths must stay on one line.

"""Layer 4 semantic conventions Engine C."""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from enum import StrEnum
from inspect import Parameter, signature
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from validator import llm_provider
from validator.conventions_rules import (
    CompiledConventionRule,
    ConventionsRules,
    ConventionWaiver,
    load_conventions_rules,
    rulebook_path,
)
from validator.semantic.config import load_semantic_config

ProviderFindingSeverity = Literal["blocking", "warning", "info"]
MAX_SOURCE_EXCERPT_CHARS = 4000
DEFAULT_REVIEW_MODEL = "claude-3-5-sonnet-latest"


class ProviderCallError(RuntimeError):
    """Raised when the configured provider call fails."""


class ProviderOutputError(ValueError):
    """Raised when provider output cannot be trusted."""


class SemanticConventionVerdict(StrEnum):
    """Semantic conventions gate verdict."""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class EngineCBase(BaseModel):
    """Strict frozen base model for Engine C payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProviderFinding(EngineCBase):
    """Finding returned by the configured provider."""

    rule_id: str
    path: str
    line: int = 1
    message: str
    severity: ProviderFindingSeverity = "warning"


class ProviderFindingBatch(EngineCBase):
    """Provider response for one semantic domain group."""

    findings: list[ProviderFinding] = Field(default_factory=list)


class SemanticFinding(EngineCBase):
    """Waiver-aware semantic convention finding."""

    rule_id: str
    domain: str
    path: str
    line: int
    message: str
    severity: ProviderFindingSeverity
    blocking: bool
    waived: bool


class SemanticConventionsResult(EngineCBase):
    """Complete Engine C result."""

    verdict: SemanticConventionVerdict
    findings: list[SemanticFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    provider_calls: int = 0


def run_semantic_conventions(
    project_root: Path,
    *,
    source_texts: Mapping[str, str] | None = None,
    rules_path: Path | None = None,
    model: str | None = None,
    today: date | None = None,
) -> SemanticConventionsResult:
    """Run Layer 4 semantic convention checks.

    Args:
        project_root: Repository root containing the compiled rulebook.
        source_texts: Optional source excerpts keyed by repository-relative path.
        rules_path: Optional explicit rulebook path.
        model: Deprecated implementation model argument. Engine C always uses a review model.
        today: Date used for waiver expiry checks; defaults to current UTC date.

    Returns:
        Deterministic PASS, FAIL, or BLOCKED result.
    """
    del model  # Deprecated: Engine C must never reuse the caller's implementation model.
    root = project_root.resolve()
    rulebook = load_conventions_rules(rules_path or rulebook_path(root))
    current_date = today or datetime.now(UTC).date()
    review_model = _configured_review_model(root)
    findings: list[SemanticFinding] = []
    provider_calls = 0
    for domain, rules in _rules_by_domain(rulebook).items():
        if not rules:
            continue
        try:
            batch = _call_domain_provider(
                domain=domain,
                rules=rules,
                source_texts=source_texts or {},
                model=review_model,
            )
            domain_findings = _normalize_findings(
                domain, rules, batch, rulebook.waivers, current_date
            )
        except (
            ProviderCallError,
            ProviderOutputError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            return SemanticConventionsResult(
                verdict=SemanticConventionVerdict.BLOCKED,
                blockers=[f"semantic provider unavailable or invalid: {exc}"],
                provider_calls=provider_calls,
            )
        provider_calls += 1
        findings.extend(domain_findings)
    has_unwaived_blocking = any(finding.blocking and not finding.waived for finding in findings)
    return SemanticConventionsResult(
        verdict=SemanticConventionVerdict.FAIL
        if has_unwaived_blocking
        else SemanticConventionVerdict.PASS,
        findings=findings,
        provider_calls=provider_calls,
    )


def _rules_by_domain(rulebook: ConventionsRules) -> dict[str, list[CompiledConventionRule]]:
    unenforceable_ids = {rule.id for rule in rulebook.unenforceable}
    grouped: dict[str, list[CompiledConventionRule]] = {}
    for rule in rulebook.rules:
        if rule.id in unenforceable_ids:
            continue
        grouped.setdefault(rule.domain, []).append(rule)
    return dict(sorted(grouped.items()))


def _configured_review_model(project_root: Path) -> str:
    configured = load_semantic_config(project_root / ".specs").review_model.strip()
    if configured:
        return configured
    provider_loader = getattr(llm_provider, "_load_provider", None)
    if callable(provider_loader):
        try:
            provider = provider_loader()
        except llm_provider.LLMProviderNotConfigured:
            provider = None
        provider_model = getattr(provider, "review_model", "")
        if isinstance(provider_model, str) and provider_model.strip():
            return provider_model.strip()
    return DEFAULT_REVIEW_MODEL


def _call_domain_provider(
    *,
    domain: str,
    rules: list[CompiledConventionRule],
    source_texts: Mapping[str, str],
    model: str | None,
) -> ProviderFindingBatch:
    prompt = _domain_prompt(domain, rules, source_texts)
    raw = _call_provider(prompt, _FINDINGS_SCHEMA, model=model)
    data: object = json.loads(raw)
    return ProviderFindingBatch.model_validate(data)


def _domain_prompt(
    domain: str,
    rules: list[CompiledConventionRule],
    source_texts: Mapping[str, str],
) -> str:
    rules_block = "\n".join(
        "\n".join(
            [
                f"- {rule.id} blocking={rule.blocking}: {rule.check}",
                f"  convention_source_excerpt: {rule.source_excerpt}",
            ]
        )
        for rule in rules
    )
    # Source excerpts are bounded so a single large file cannot crowd out the rulebook context.
    sources_block = "\n\n".join(
        f"## File: {path}\n{text[:MAX_SOURCE_EXCERPT_CHARS]}"
        for path, text in sorted(source_texts.items())
    )
    schema_context = json.dumps(_FINDINGS_SCHEMA["schema"], sort_keys=True)
    return (
        f"Review semantic convention domain {domain}. Temperature: 0.\n"
        "Return only JSON matching the schema. Do not compute a final verdict.\n\n"
        f"## Output schema\n{schema_context}\n\n"
        f"## Rules\n{rules_block}\n\n## Source excerpts\n{sources_block or '(none provided)'}"
    )


def _call_provider(prompt: str, json_schema: dict[str, object], *, model: str | None) -> str:
    provider_call = cast(Callable[..., str], llm_provider.call_llm)
    parameters = signature(provider_call).parameters.values()
    supports_temperature = any(
        parameter.kind is Parameter.VAR_KEYWORD or parameter.name == "temperature"
        for parameter in parameters
    )
    try:
        if supports_temperature:
            return provider_call(prompt, json_schema=json_schema, model=model, temperature=0)
        return provider_call(prompt, json_schema=json_schema, model=model)
    except (llm_provider.LLMProviderNotConfigured, OSError, RuntimeError, TimeoutError) as exc:
        raise ProviderCallError(str(exc)) from exc


def _normalize_findings(
    domain: str,
    rules: list[CompiledConventionRule],
    batch: ProviderFindingBatch,
    waivers: list[ConventionWaiver],
    today: date,
) -> list[SemanticFinding]:
    by_id = {rule.id: rule for rule in rules}
    unknown = sorted(
        {finding.rule_id for finding in batch.findings if finding.rule_id not in by_id}
    )
    if unknown:
        raise ProviderOutputError(f"unknown semantic rule ids: {', '.join(unknown)}")
    normalized: list[SemanticFinding] = []
    for finding in batch.findings:
        rule = by_id[finding.rule_id]
        normalized.append(
            SemanticFinding(
                rule_id=finding.rule_id,
                domain=rule.domain,
                path=finding.path,
                line=finding.line,
                message=finding.message,
                severity=finding.severity,
                blocking=rule.blocking,
                waived=_is_waived(finding, waivers, today),
            )
        )
    return normalized


def _is_waived(finding: ProviderFinding, waivers: list[ConventionWaiver], today: date) -> bool:
    for waiver in waivers:
        if waiver.rule_id != finding.rule_id:
            continue
        if waiver.path_glob and not fnmatch.fnmatch(finding.path, waiver.path_glob):
            continue
        if date.fromisoformat(waiver.expires) < today:
            continue
        return True
    return False


_FINDINGS_SCHEMA: dict[str, object] = {
    "name": "semantic_conventions_findings",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "rule_id": {"type": "string"},
                        "path": {"type": "string"},
                        "line": {"type": "integer"},
                        "message": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["blocking", "warning", "info"],
                        },
                    },
                    "required": ["rule_id", "path", "line", "message", "severity"],
                },
            }
        },
        "required": ["findings"],
        "additionalProperties": False,
    },
}

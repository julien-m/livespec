"""Rule evaluator + report builder for `/spec.verify-output`.

# @spec FR-007: verify-output evaluator
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-007
# @spec FR-010: when-branch activator
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-010
# @spec AC-011: rule independence (no short-circuit)
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#ac-011
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from . import placeholders
from .expectations import ExpectationsFile, Rule, VerifyBlock, WhenBranch
from .outcome import Outcome, classify, exit_code_for
from .run_artifact import RunArtifact

RuleStatus = str  # "PASS" | "FAIL" | "SKIPPED"


def _empty_rule_results() -> list[RuleResult]:
    """Typed default factory for ``list[RuleResult]`` dataclass fields."""
    return []


@dataclass
class RuleResult:
    """The evaluation result for a single rule."""

    rule: Rule
    status: RuleStatus
    detail: str


@dataclass
class VerifyReport:
    """Full report returned by :func:`evaluate`."""

    command: str
    source_path: Path
    artifact_path: Path | None
    results: list[RuleResult] = field(default_factory=_empty_rule_results)
    outcome: Outcome = "blocked"
    blocked_reason: str | None = None

    @property
    def exit_code(self) -> int:
        return exit_code_for(self.outcome)


@dataclass
class ActiveRuleSet:
    """The flattened rule set after `when:` activation."""

    must: list[Rule]
    may: list[Rule]
    must_not: list[Rule]
    activated_flags: list[str]


def activate_when_branches(
    verify: VerifyBlock,
    flags: list[str],
) -> ActiveRuleSet:
    """Accumulate base rules plus every matching ``when:`` branch (FR-010)."""
    must = list(verify.must)
    may = list(verify.may)
    must_not = list(verify.must_not)
    activated: list[str] = []
    for branch in verify.when:
        if branch.flag in flags:
            activated.append(branch.flag)
            must.extend(branch.must)
            may.extend(branch.may)
            must_not.extend(branch.must_not)
    return ActiveRuleSet(
        must=must,
        may=may,
        must_not=must_not,
        activated_flags=activated,
    )


def evaluate(
    expectations: ExpectationsFile,
    artifact: RunArtifact,
    *,
    scenario_flags: list[str] | None = None,
    feature: str | None = None,
    artifact_path: Path | None = None,
) -> VerifyReport:
    """Evaluate the verify block against a run artifact.

    Independence invariant (AC-011): ``must``, ``may``, ``must_not`` are
    three independent buckets. NO short-circuit between groups; every rule
    produces a :class:`RuleResult`.
    """
    flags = list(set((scenario_flags or []) + list(artifact.flags)))
    active = activate_when_branches(expectations.verify, flags)
    run_date = placeholders.run_date_from_timestamp(artifact.timestamp)

    raw_output = artifact.stdout + "\n" + artifact.stderr
    results: list[RuleResult] = []

    # Evaluate each bucket independently — no short-circuit, no early return.
    for rule in active.must:
        results.append(_evaluate_rule(rule, artifact, raw_output, feature, run_date))
    for rule in active.may:
        results.append(_evaluate_rule(rule, artifact, raw_output, feature, run_date))
    for rule in active.must_not:
        results.append(_evaluate_rule(rule, artifact, raw_output, feature, run_date))

    any_must_failed = any(
        r.status == "FAIL"
        and r.rule.verb in ("must", "must_not")
        for r in results
    )
    outcome = classify(
        artifact_exit_code=artifact.exit_code,
        any_must_failed=any_must_failed,
    )

    return VerifyReport(
        command=expectations.command,
        source_path=expectations.source_path,
        artifact_path=artifact_path,
        results=results,
        outcome=outcome,
    )


def blocked_report(
    *,
    command: str,
    source_path: Path | None,
    artifact_path: Path | None,
    reason: str,
) -> VerifyReport:
    """Build a report for a blocked verification (no artifact, malformed override…)."""
    return VerifyReport(
        command=command,
        source_path=source_path or Path(),
        artifact_path=artifact_path,
        results=[],
        outcome="blocked",
        blocked_reason=reason,
    )


# ---------- rule evaluators ----------


def _evaluate_rule(
    rule: Rule,
    artifact: RunArtifact,
    raw_output: str,
    feature: str | None,
    run_date: str,
) -> RuleResult:
    """Dispatch to the appropriate evaluator and apply verb semantics."""
    if rule.kind == "contains":
        return _eval_contains(rule, raw_output, feature, run_date)
    if rule.kind == "exists":
        return _eval_exists(rule, artifact, feature, run_date)
    if rule.kind == "exit_code":
        return _eval_exit_code(rule, artifact)
    if rule.kind == "produces_artifact":
        return _eval_produces_artifact(rule, artifact, feature, run_date)
    return RuleResult(rule, "SKIPPED", f"unknown rule kind: {rule.kind}")


def _eval_contains(
    rule: Rule,
    raw_output: str,
    feature: str | None,
    run_date: str,
) -> RuleResult:
    needle = placeholders.resolve(str(rule.payload), feature=feature, run_date=run_date)
    present = needle in raw_output
    return _apply_verb(rule, present, f"substring {needle!r}")


def _eval_exists(
    rule: Rule,
    artifact: RunArtifact,
    feature: str | None,
    run_date: str,
) -> RuleResult:
    raw_path = placeholders.resolve(str(rule.payload), feature=feature, run_date=run_date)
    target = Path(raw_path)
    if not target.is_absolute():
        target = Path(artifact.cwd) / raw_path
    exists = target.exists()
    return _apply_verb(rule, exists, f"path {raw_path}")


def _eval_exit_code(rule: Rule, artifact: RunArtifact) -> RuleResult:
    expected = int(rule.payload)
    actual = artifact.exit_code
    matched = expected == actual
    return _apply_verb(rule, matched, f"exit_code expected={expected} actual={actual}")


def _eval_produces_artifact(
    rule: Rule,
    artifact: RunArtifact,
    feature: str | None,
    run_date: str,
) -> RuleResult:
    payload: dict[str, Any] = rule.payload
    raw_path = placeholders.resolve(str(payload["path"]), feature=feature, run_date=run_date)
    sections: list[str] = list(payload.get("contains_sections") or [])
    target = Path(raw_path)
    if not target.is_absolute():
        target = Path(artifact.cwd) / raw_path
    if not target.exists():
        return _apply_verb(rule, False, f"artifact missing at {raw_path}")
    try:
        body = target.read_text(encoding="utf-8")
    except OSError as exc:
        return RuleResult(rule, "FAIL", f"read error: {exc}")
    missing = [s for s in sections if s not in body]
    ok = not missing
    detail = f"artifact {raw_path}" + (f" missing sections: {missing}" if missing else "")
    return _apply_verb(rule, ok, detail)


def _apply_verb(rule: Rule, condition: bool, detail: str) -> RuleResult:
    """Map a boolean condition to PASS/FAIL according to the rule's verb."""
    if rule.verb == "must":
        return RuleResult(rule, "PASS" if condition else "FAIL", detail)
    if rule.verb == "must_not":
        # must_not PASSES when the condition is False (substring absent etc).
        return RuleResult(rule, "PASS" if not condition else "FAIL", detail)
    # may — never blocking; PASS when condition true, SKIPPED-informational otherwise.
    return RuleResult(rule, "PASS" if condition else "SKIPPED", detail)


def render_human(report: VerifyReport) -> str:
    """Format a report as a human-readable table."""
    lines: list[str] = []
    lines.append(f"verify-output  command={report.command}")
    lines.append(f"source         {report.source_path}")
    if report.artifact_path is not None:
        lines.append(f"artifact       {report.artifact_path}")
    if report.blocked_reason:
        lines.append(f"blocked_reason {report.blocked_reason}")
    lines.append("")
    if report.results:
        lines.append(f"{'verb':<10}{'kind':<22}{'status':<10}detail")
        lines.append("-" * 80)
        for r in report.results:
            lines.append(
                f"{r.rule.verb:<10}{r.rule.kind:<22}{r.status:<10}{r.detail}"
            )
        lines.append("")
    lines.append(f"outcome   {report.outcome}")
    lines.append(f"exit_code {report.exit_code}")
    return "\n".join(lines)


def render_json(report: VerifyReport) -> dict[str, Any]:
    """Format a report as a JSON-serializable dict."""
    return {
        "command": report.command,
        "source_path": str(report.source_path),
        "artifact_path": str(report.artifact_path) if report.artifact_path else None,
        "outcome": report.outcome,
        "exit_code": report.exit_code,
        "blocked_reason": report.blocked_reason,
        "results": [
            {
                "verb": r.rule.verb,
                "kind": r.rule.kind,
                "payload": _jsonable_payload(r.rule),
                "status": r.status,
                "detail": r.detail,
            }
            for r in report.results
        ],
    }


def _jsonable_payload(rule: Rule) -> Any:
    """Render rule payloads safely for JSON output."""
    if isinstance(rule.payload, dict):
        return cast(dict[str, Any], rule.payload)  # type: ignore[arg-type]
    return rule.payload


__all__ = [
    "ActiveRuleSet",
    "RuleResult",
    "VerifyReport",
    "activate_when_branches",
    "blocked_report",
    "evaluate",
    "render_human",
    "render_json",
]


# Reuse to silence import linters; underscore noop.
_WhenBranch = WhenBranch

# LiveSpec traceability anchors
# @spec(AC-005)
# @spec(AC-008)
# @spec(AC-009)

"""Shared verify-output rule engine consumed by ``goal archive`` and ``verify-output``.

# @spec FR-006: shared engine 4 kinds + cumulative when
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-006
# @spec FR-007: outcome + placeholder wiring
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-007
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from .outcome import Outcome, classify
from .placeholders import resolve, run_date_from_timestamp
from .verify_output_report import render_report, to_json_envelope

RuleStatus = Literal["PASS", "FAIL", "SKIP"]


@dataclass(frozen=True)
class RuleResult:
    """Evaluation result for one verify rule."""

    verb: str
    kind: str
    status: RuleStatus
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Return the JSON-serializable rule result."""
        return {"verb": self.verb, "kind": self.kind, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class VerifyReport:
    """Engine output: 4-state outcome plus per-rule results."""

    outcome: Outcome
    rules: tuple[RuleResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable ``verify_result`` artifact field."""
        return {"outcome": self.outcome, "rules": [rule.to_dict() for rule in self.rules]}


# @spec AC-008: shared rule engine, cumulative when-branches, no short-circuit
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#ac-008
def evaluate_rules(
    verify_rules: dict[str, Any],
    *,
    artifact: dict[str, Any],
    active_flags: list[str],
    feature: str | None,
    project_root: Path,
    goal_incomplete: bool = False,
    receipt_error: bool = False,
) -> VerifyReport:
    """Evaluate every active verify rule against a RunArtifact v2.

    Args:
        verify_rules: Raw rule buckets (``must``/``may``/``must_not``/``when``)
            as copied into the artifact from the goal contract.
        artifact: RunArtifact v2 mapping (provides exit_code, transcripts,
            timestamp).
        active_flags: Flags used to activate ``when:`` branches cumulatively.
        feature: Value substituted for the ``<feature>`` placeholder.
        project_root: Root against which ``exists``/``produces_artifact``
            paths are resolved.
        goal_incomplete: True when at least one required goal task is pending;
            counts as a must-level failure (drift, EC-002).
        receipt_error: True when a referenced receipt failed integrity
            re-verification; forces the ``error`` outcome (AC-006).

    Returns:
        A :class:`VerifyReport` with one :class:`RuleResult` per active rule.
    """
    run_date = run_date_from_timestamp(str(artifact.get("timestamp", "")))
    results = [
        _evaluate_rule(
            rule,
            artifact=artifact,
            feature=feature,
            run_date=run_date,
            project_root=project_root,
        )
        for rule in _active_rules(verify_rules, active_flags)
    ]
    any_must_failed = any(
        result.status == "FAIL" and result.verb in ("must", "must_not") for result in results
    )
    # EC-011: a null exit_code is honest absence — exit_code rules SKIP above,
    # and the classification must not degrade to blocked/error because of it.
    raw_exit = artifact.get("exit_code")
    effective_exit = raw_exit if isinstance(raw_exit, int) else 0
    outcome = classify(
        artifact_exit_code=effective_exit,
        any_must_failed=any_must_failed or goal_incomplete,
    )
    if receipt_error:
        # AC-006: a tampered/missing receipt invalidates the chain of proof.
        outcome = "error"
    return VerifyReport(outcome=outcome, rules=tuple(results))


def _active_rules(verify_rules: dict[str, Any], active_flags: list[str]) -> list[dict[str, Any]]:
    """Collect base rules plus every when-branch matching an active flag.

    Branch accumulation strategy (039 AC-009): each branch whose flag is
    present in ``active_flags`` contributes its rules, ANDed with the base
    buckets; branches never replace one another.
    """
    rules = _bucket_rules(verify_rules)
    when_raw = verify_rules.get("when")
    branches = cast(list[object], when_raw) if isinstance(when_raw, list) else []
    for branch_obj in branches:
        if not isinstance(branch_obj, dict):
            continue
        branch = cast(dict[str, Any], branch_obj)
        if str(branch.get("flag", "")) in active_flags:
            rules.extend(_bucket_rules(branch))
    return rules


def _bucket_rules(container: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the must/may/must_not buckets of one rule container."""
    rules: list[dict[str, Any]] = []
    for verb in ("must", "may", "must_not"):
        bucket = container.get(verb)
        if not isinstance(bucket, list):
            continue
        for rule_obj in cast(list[object], bucket):
            if isinstance(rule_obj, dict):
                rules.append(cast(dict[str, Any], rule_obj))
    return rules


def _evaluate_rule(
    rule: dict[str, Any],
    *,
    artifact: dict[str, Any],
    feature: str | None,
    run_date: str,
    project_root: Path,
) -> RuleResult:
    """Evaluate one rule; SKIP statuses encode honest evidence absence."""
    verb = str(rule.get("verb", "must"))
    kind = str(rule.get("kind", ""))
    payload: Any = rule.get("payload")
    if kind == "exit_code":
        return _evaluate_exit_code(verb, payload, artifact)
    if kind == "contains":
        return _evaluate_contains(verb, payload, artifact, feature, run_date)
    if kind == "exists":
        return _evaluate_exists(verb, payload, feature, run_date, project_root)
    if kind == "produces_artifact":
        return _evaluate_produces_artifact(verb, payload, feature, run_date, project_root)
    return RuleResult(verb=verb, kind=kind, status="SKIP", detail=f"unknown rule kind {kind!r}")


def _evaluate_exit_code(verb: str, payload: Any, artifact: dict[str, Any]) -> RuleResult:
    exit_code = artifact.get("exit_code")
    if not isinstance(exit_code, int):
        # EC-011: archive ran without --exit-code — honest absence, never a failure.
        return RuleResult(
            verb=verb,
            kind="exit_code",
            status="SKIP",
            detail="exit_code not recorded in artifact",
        )
    expected = int(payload) if isinstance(payload, int | str) else payload
    matched = exit_code == expected
    detail = f"exit_code expected={expected} actual={exit_code}"
    return RuleResult(verb=verb, kind="exit_code", status=_status(verb, matched), detail=detail)


def _evaluate_contains(
    verb: str,
    payload: Any,
    artifact: dict[str, Any],
    feature: str | None,
    run_date: str,
) -> RuleResult:
    needle = resolve(str(payload), feature=feature, run_date=run_date)
    if "stdout" not in artifact and "stderr" not in artifact:
        # AC-005: no transcript embedded — contains rules degrade to SKIP.
        return RuleResult(
            verb=verb,
            kind="contains",
            status="SKIP",
            detail=(
                f"substring {needle!r} not checked — no transcript embedded "
                "(archive ran without --stdout-file/--stderr-file)"
            ),
        )
    transcript = f"{artifact.get('stdout', '')}\n{artifact.get('stderr', '')}"
    matched = needle in transcript
    return RuleResult(
        verb=verb,
        kind="contains",
        status=_status(verb, matched),
        detail=f"substring {needle!r}",
    )


def _evaluate_exists(
    verb: str,
    payload: Any,
    feature: str | None,
    run_date: str,
    project_root: Path,
) -> RuleResult:
    rel = resolve(str(payload), feature=feature, run_date=run_date)
    target = _confined_project_path(project_root, rel)
    if target is None:
        return RuleResult(
            verb=verb,
            kind="exists",
            status=_status(verb, False),
            detail=f"path {rel} escapes project root",
        )
    matched = target.exists()
    return RuleResult(verb=verb, kind="exists", status=_status(verb, matched), detail=f"path {rel}")


def _evaluate_produces_artifact(
    verb: str,
    payload: Any,
    feature: str | None,
    run_date: str,
    project_root: Path,
) -> RuleResult:
    data = cast(dict[str, Any], payload) if isinstance(payload, dict) else {"path": str(payload)}
    rel = resolve(str(data.get("path", "")), feature=feature, run_date=run_date)
    sections_raw = data.get("contains_sections")
    sections = (
        [str(section) for section in cast(list[object], sections_raw)]
        if isinstance(sections_raw, list)
        else []
    )
    target = _confined_project_path(project_root, rel)
    if target is None:
        return RuleResult(
            verb=verb,
            kind="produces_artifact",
            status=_status(verb, matched=False),
            detail=f"artifact {rel} escapes project root",
        )
    if not target.exists():
        return RuleResult(
            verb=verb,
            kind="produces_artifact",
            status=_status(verb, matched=False),
            detail=f"artifact {rel} missing",
        )
    content = target.read_text(encoding="utf-8", errors="replace")
    missing = [section for section in sections if section not in content]
    matched = not missing
    detail = f"artifact {rel}" + (f" missing sections {missing}" if missing else "")
    return RuleResult(
        verb=verb,
        kind="produces_artifact",
        status=_status(verb, matched),
        detail=detail,
    )


def _confined_project_path(project_root: Path, rel: str) -> Path | None:
    """Resolve a rule path only when it stays inside ``project_root``."""
    root = project_root.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def _status(verb: str, matched: bool) -> RuleStatus:
    """Map a raw match to PASS/FAIL — must_not inverts the polarity."""
    if verb == "must_not":
        return "PASS" if not matched else "FAIL"
    return "PASS" if matched else "FAIL"


__all__ = [
    "RuleResult",
    "RuleStatus",
    "VerifyReport",
    "evaluate_rules",
    "render_report",
    "to_json_envelope",
]

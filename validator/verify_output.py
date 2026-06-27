# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-007)

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
    active, replace_base = _active_rules(verify_rules, active_flags)
    results = [
        _evaluate_rule(
            rule,
            artifact=artifact,
            feature=feature,
            run_date=run_date,
            project_root=project_root,
        )
        for rule in active
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
        ignore_exit_code=replace_base,
    )
    if receipt_error:
        # AC-006: a tampered/missing receipt invalidates the chain of proof.
        outcome = "error"
    return VerifyReport(outcome=outcome, rules=tuple(results))


def _active_rules(
    verify_rules: dict[str, Any], active_flags: list[str]
) -> tuple[list[dict[str, Any]], bool]:
    """Collect base rules plus every when-branch matching an active flag.

    Branch accumulation strategy (039 AC-009): each branch whose flag is
    present in ``active_flags`` contributes its rules, ANDed with the base
    buckets; branches never replace one another.

    Exception (C14): a matched branch carrying ``replace_base: true`` drops the
    base bucket rules entirely (only the active branches' rules apply) and signals
    that the exit-code→error classification must be relaxed. This lets a read-only
    gate mode (e.g. ``--pre-impl``) own its own contract without inheriting the
    normal-mode base rules. Returns ``(rules, replace_base)``.
    """
    base_rules = _bucket_rules(verify_rules)
    branch_rules: list[dict[str, Any]] = []
    replace_base = False
    when_raw = verify_rules.get("when")
    branches = cast(list[object], when_raw) if isinstance(when_raw, list) else []
    for branch_obj in branches:
        if not isinstance(branch_obj, dict):
            continue
        branch = cast(dict[str, Any], branch_obj)
        if str(branch.get("flag", "")) in active_flags:
            if branch.get("replace_base") is True:
                replace_base = True
            branch_rules.extend(_bucket_rules(branch))
    rules = branch_rules if replace_base else base_rules + branch_rules
    return rules, replace_base


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
    if kind == "receipt_verdict":
        return _evaluate_receipt_verdict(verb, payload, artifact, project_root)
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
    if target.is_dir():
        # A directory path cannot be read as text. Existence semantics apply: the
        # artifact (directory) is present. Section checks are file-only — if any are
        # requested against a directory, that is an explicit non-match, never a crash.
        if sections:
            return RuleResult(
                verb=verb,
                kind="produces_artifact",
                status=_status(verb, matched=False),
                detail=f"artifact {rel} is a directory; cannot check sections {sections}",
            )
        return RuleResult(
            verb=verb,
            kind="produces_artifact",
            status=_status(verb, matched=True),
            detail=f"artifact {rel} (directory present)",
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


def _evaluate_receipt_verdict(
    verb: str,
    payload: Any,
    artifact: dict[str, Any],
    project_root: Path,
) -> RuleResult:
    """Require an archived receipt kind to carry an expected verdict."""
    if not isinstance(payload, dict):
        return RuleResult(
            verb=verb,
            kind="receipt_verdict",
            status=_status(verb, False),
            detail="receipt_verdict payload must be a mapping",
        )
    data = cast(dict[str, Any], payload)
    receipt_kind = str(data.get("kind", ""))
    expected = str(data.get("verdict", "PASS"))
    if not receipt_kind or expected not in {"PASS", "FAIL", "BLOCKED"}:
        return RuleResult(
            verb=verb,
            kind="receipt_verdict",
            status=_status(verb, False),
            detail="receipt_verdict requires kind and verdict PASS|FAIL|BLOCKED",
        )
    if receipt_kind == "conventions" and data.get("required_if_exists", True) is not False:
        gates = project_root / ".specs" / "conventions-gates.yaml"
        if not gates.exists():
            return RuleResult(
                verb=verb,
                kind="receipt_verdict",
                status="SKIP",
                detail="conventions gates absent; receipt_verdict skipped",
            )
    receipts_raw = artifact.get("receipts")
    receipts = cast(list[object], receipts_raw) if isinstance(receipts_raw, list) else []
    matches = [
        cast(dict[str, Any], item)
        for item in receipts
        if isinstance(item, dict) and item.get("kind") == receipt_kind
    ]
    if not matches:
        return RuleResult(
            verb=verb,
            kind="receipt_verdict",
            status=_status(verb, False),
            detail=f"receipt {receipt_kind} missing",
        )
    actual = str(matches[-1].get("verdict", ""))
    verified = matches[-1].get("verified") is True
    if not verified:
        return RuleResult(
            verb=verb,
            kind="receipt_verdict",
            status=_status(verb, False),
            detail=f"receipt {receipt_kind} unverified",
        )
    matched = verified and actual == expected
    return RuleResult(
        verb=verb,
        kind="receipt_verdict",
        status=_status(verb, matched),
        detail=f"receipt {receipt_kind} expected={expected} actual={actual} verified={verified}",
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

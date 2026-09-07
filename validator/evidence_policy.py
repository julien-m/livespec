"""Explicit task proof purpose, independent of task category (078 FR-009)."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EVIDENCE_POLICY_VERSION = "2"
SUPPORTED_EVIDENCE_POLICIES = ("1", "2")


def contract_evidence_policy(contract: Mapping[str, object]) -> object:
    """Read the immutable canonical policy before optional serialized mirrors."""
    raw = contract.get("canonical_json")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and "evidence_policy_version" in parsed:
            return parsed["evidence_policy_version"]
    canonical = contract.get("canonical")
    if isinstance(canonical, Mapping) and "evidence_policy_version" in canonical:
        return canonical["evidence_policy_version"]
    return contract.get("evidence_policy_version")


def current_contract_integrity_error(contract: Mapping[str, object]) -> str | None:
    """Bind current serialized policy, scope and task evidence to the hashed canonical contract."""
    canonical = contract.get("canonical")
    if contract_evidence_policy(contract) is None:
        return None  # Historical contracts retain their original validation policy.
    if contract_evidence_policy(contract) not in SUPPORTED_EVIDENCE_POLICIES:
        return "unknown_evidence_policy_version"
    if not isinstance(canonical, Mapping):
        return "current_contract_canonical_missing"
    raw = contract.get("canonical_json")
    if not isinstance(raw, str):
        return "current_contract_canonical_json_missing"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return "current_contract_canonical_json_invalid"
    if parsed != canonical or hashlib.sha256(raw.encode()).hexdigest() != contract.get("goal_hash"):
        return "current_contract_canonical_hash_mismatch"
    for field in ("command", "feature", "normalized_flags", "tasks"):
        if contract.get(field) != canonical.get(field):
            return f"current_contract_mirror_mismatch:{field}"
    if "evidence_policy_version" in contract and contract[
        "evidence_policy_version"
    ] != canonical.get("evidence_policy_version"):
        return "current_contract_mirror_mismatch:evidence_policy_version"
    return None


_MARKER = re.compile(
    r"\s*<!-- evidence:(documentary|review|execution)((?: [a-z-]+:[a-z0-9-]+)*) -->\s*$"
)


def strip_evidence_marker(description: str) -> str:
    """Preserve historical task text and IDs when metadata is added."""
    return _MARKER.sub("", description).strip()


def apply_evidence_policy(
    tasks: list[dict[str, Any]],
    skill_path: Path,
    *,
    project_root: Path | None = None,
    feature: str | None = None,
) -> None:
    """Classify exact declared task rows; unclassified tasks never fall back to prose."""
    declared, metadata = _declared_evidence(skill_path)
    for task in tasks:
        description = str(task["description"])
        description = re.sub(r" \[feature: [^]]+\]$", "", description)
        task_id = str(task["id"])
        specialized = task_id.startswith(("visual.", "finalize.", "archive.", "hooks.", "qe."))
        kind = "documentary" if specialized else declared.get(description, "unclassified")
        attributes = metadata.get(description, {})
        if "applicable" in attributes:
            from .evidence_applicability import resolve_applicability

            applicability = resolve_applicability(project_root, feature, attributes["applicable"])
            task["applicability"] = applicability
            if applicability["applicable"] is False:
                kind = "documentary"
        task["evidence_kind"] = kind
        _bind_review_kind(task, attributes)
        if "ac-scope" in attributes:
            task["acceptance_scope"] = attributes["ac-scope"]
        if "outcome" in attributes:
            task["evidence_expected_outcome"] = attributes["outcome"]
        _bind_acceptance_kind(task, attributes)
        if kind in ("execution", "review"):
            task["required_evidence"] = [
                item
                for item in task["required_evidence"]
                if item not in ("observable_output_or_artifact", "success_criteria_met")
            ]
            task["required_evidence"].append(f"{kind}_receipt_path")

    from .acceptance_evidence import bind_final_acceptance_scopes

    bind_final_acceptance_scopes(tasks, project_root, feature)


def _declared_evidence(skill_path: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    declared: dict[str, str] = {}
    metadata: dict[str, dict[str, str]] = {}
    for line in skill_path.read_text(encoding="utf-8").splitlines():
        marker = _MARKER.search(line)
        if marker:
            text = re.sub(r"^-\s+\[[^]]*\]\s*", "", line.strip())
            text = re.sub(r"^\[[^]]*\]\s*", "", text)
            declared[strip_evidence_marker(text)] = marker.group(1)
            attributes = dict(pair.split(":", 1) for pair in marker.group(2).split())
            if set(attributes) - {"ac-scope", "applicable", "outcome", "review-kind", "ac-binding"}:
                raise ValueError("unknown_evidence_metadata")
            metadata[strip_evidence_marker(text)] = attributes
    return declared, metadata


def _bind_acceptance_kind(task: dict[str, Any], attributes: dict[str, str]) -> None:
    from .acceptance_evidence import is_final_acceptance_task

    if "ac-binding" not in attributes:
        return
    if attributes["ac-binding"] != "reviewed-spec":
        raise ValueError("unknown_acceptance_binding")
    if not is_final_acceptance_task(task) or "applicable" in attributes:
        raise ValueError("reviewed_spec_binding_requires_unconditional_final_acceptance")
    task["acceptance_binding"] = "reviewed-spec"


def _bind_review_kind(task: dict[str, Any], attributes: dict[str, str]) -> None:
    if task["evidence_kind"] == "review":
        kind = attributes.get("review-kind")
        if kind not in ("spec", "plan"):
            raise ValueError("review_kind_required")
        task.setdefault("expected_evidence", {})["review_kind"] = kind
    elif "review-kind" in attributes:
        raise ValueError("review_kind_requires_review_evidence")


def typed_evidence_missing(
    task: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    project_root: Path | None,
) -> list[str]:
    """Verify current proof policy; immutable contracts without a policy stay historical."""
    version = contract_evidence_policy(contract)
    if version is None:
        return []
    if version not in SUPPORTED_EVIDENCE_POLICIES:
        return ["unknown_evidence_policy_version"]
    kind = task.get("evidence_kind")
    if kind == "documentary":
        return _documentary_applicability_missing(task, contract, project_root)
    if kind not in ("review", "execution"):
        return ["explicit_evidence_kind_required"]
    feature = contract.get("feature")
    path = evidence.get(f"{kind}_receipt_path")
    if not isinstance(path, str) or not path:
        return [f"{kind}_receipt_path"]
    if project_root is None or not isinstance(feature, str) or not feature:
        return ["project_and_feature_scope_required"]
    receipt = Path(path)
    receipt = receipt if receipt.is_absolute() else project_root / receipt
    try:
        receipt.resolve().relative_to(project_root.resolve())
        if kind == "execution":
            return _execution_missing(
                task, receipt, project_root, feature, policy=str(version), evidence=evidence
            )
        return _semantic_review_missing(task, receipt, project_root, feature)
    except (OSError, ValueError, TypeError) as exc:
        return [f"{kind}_receipt_invalid:{exc}"]


def _semantic_review_missing(
    task: Mapping[str, Any], receipt: Path, project_root: Path, feature: str
) -> list[str]:
    """Bind semantic review consumption to any explicitly declared immutable purpose."""
    from .semantic.review_api import verify_feature_review

    expected = task.get("expected_evidence", {})
    model = expected.get("reviewer_model", "") if isinstance(expected, dict) else ""
    budget = expected.get("review_max_chars") if isinstance(expected, dict) else None
    review_kind = expected.get("review_kind") if isinstance(expected, dict) else None
    if review_kind not in (None, "spec", "plan"):
        return ["unknown_review_kind"]
    review_valid = verify_feature_review(
        project_root,
        feature,
        receipt,
        model=str(model),
        max_chars=budget if isinstance(budget, int) else None,
        expected_kind=review_kind,
    )
    return [] if review_valid else ["review_receipt_incomplete_or_stale"]


def _execution_missing(
    task: Mapping[str, Any],
    receipt: Path,
    project_root: Path,
    feature: str,
    *,
    policy: str = "1",
    evidence: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate observed RED or the declared acceptance scope through the same runner verifier."""
    from .execution_evidence import verify_execution_receipt
    from .fix_acceptance_scope import _fix_selection_missing

    if selection_missing := _fix_selection_missing(task, project_root, feature):
        return selection_missing
    if task.get("evidence_expected_outcome") == "red":
        from .execution_evidence import verify_execution_observation

        observed = verify_execution_observation(
            receipt,
            project_root,
            feature,
            "red",
            evidence_policy="1" if policy == "1" else "2",
        )
        return [] if observed.valid else list(observed.gaps)

    if policy == "2" and task.get("acceptance_scope") == "feature":
        from .acceptance_evidence import verify_acceptance_evidence

        return verify_acceptance_evidence(task, evidence or {}, receipt, project_root, feature)

    required = task.get("required_acs", ())
    if task.get("acceptance_scope") == "feature":
        text = (project_root / ".specs/features" / feature / "spec.md").read_text()
        required = tuple(
            f"{feature}:{local}" for local in sorted(set(re.findall(r"\bAC-\d+\b", text)))
        )
        if not required:
            return ["feature_acceptance_scope_empty"]
    result = verify_execution_receipt(
        receipt,
        project_root=project_root,
        feature=feature,
        required_acs=tuple(required),
        evidence_policy="1" if policy == "1" else "2",
    )
    return [] if result.valid else list(result.gaps)


def _documentary_applicability_missing(
    task: Mapping[str, Any],
    contract: Mapping[str, Any],
    project_root: Path | None,
) -> list[str]:
    applicability = task.get("applicability")
    if isinstance(applicability, dict) and applicability.get("applicable") is False:
        from .evidence_applicability import resolve_applicability

        current = resolve_applicability(
            project_root,
            str(contract.get("feature") or ""),
            str(applicability.get("predicate")),
        )
        if current.get("applicable") is not False:
            return ["task_applicability_changed_recompile_required"]
    return []

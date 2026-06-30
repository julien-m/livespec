"""Validation for ARS source decision manifests."""

from __future__ import annotations

from collections import Counter
from typing import Any


def validate_rule_decision_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return blocking decision-manifest defects."""
    issues: list[str] = []
    issues.extend(
        f"catalog_load_error:{error}" for error in manifest.get("catalog_load_errors", [])
    )
    decisions = manifest["decisions"]
    undecided = _undecided_sources(decisions)
    if manifest["total_source_count"] != len(decisions):
        issues.append("total_source_count_mismatch")
    if manifest["decided_source_count"] != len(decisions) - len(undecided):
        issues.append("decided_source_count_mismatch")
    if manifest["undecided_source_count"] != len(undecided):
        issues.append("undecided_source_count_mismatch")
    if manifest["undecided_source_count"] != 0:
        issues.append("undecided_source_count_nonzero")
    expected_counts = dict(sorted(Counter(d["rule_decision"]["kind"] for d in decisions).items()))
    if manifest["decision_kind_counts"] != expected_counts:
        issues.append("decision_kind_counts_mismatch")
    for decision in decisions:
        kind = decision["rule_decision"]["kind"]
        issues.extend(_decision_identity_issues(decision))
        if kind in {"executable", "generated-executable"}:
            issues.extend(_executable_issues(decision))
        else:
            issues.extend(_non_executable_issues(decision))
    for excluded in manifest["excluded_sources"]:
        issues.extend(_excluded_issues(excluded))
    return issues


def _undecided_sources(decisions: list[dict[str, Any]]) -> list[str]:
    return [d["source_path"] for d in decisions if not d["rule_decision"]["decision_id"]]


def _executable_issues(decision: dict[str, Any]) -> list[str]:
    rule = decision["rule_decision"]
    issues: list[str] = []
    if not rule["rule_ids"]:
        issues.append(f"missing_rule_ids:{decision['source_path']}")
    if not rule["backend_ids"]:
        issues.append(f"missing_backend:{decision['source_path']}")
    if not rule["detector_ids"]:
        issues.append(f"missing_detectors:{decision['source_path']}")
    if not rule["fixture_families"]:
        issues.append(f"missing_fixtures:{decision['source_path']}")
    if not rule["test_ids"]:
        issues.append(f"missing_tests:{decision['source_path']}")
    if not rule["test_ids"] or not rule["deterministic_test_evidence"]:
        issues.append(f"missing_deterministic_test_evidence:{decision['source_path']}")
    if rule["missing_capability"]:
        issues.append(f"executable_has_missing_capability:{decision['source_path']}")
    if rule["non_blocking"]:
        issues.append(f"executable_non_blocking:{decision['source_path']}")
    if rule["kind"] == "generated-executable":
        issues.extend(_generated_executable_issues(decision))
    return issues


def _decision_identity_issues(decision: dict[str, Any]) -> list[str]:
    rule = decision["rule_decision"]
    issues: list[str] = []
    if not rule["decision_id"]:
        issues.append(f"missing_decision_id:{decision['source_path']}")
    if not rule["reason"]:
        issues.append(f"missing_reason:{decision['source_path']}")
    if not rule["decision_anchor"]:
        issues.append(f"missing_decision_anchor:{decision['source_path']}")
    if rule["decision_kind"] != rule["kind"]:
        issues.append(f"decision_kind_mismatch:{decision['source_path']}")
    if rule["source_path"] != decision["source_path"]:
        issues.append(f"rule_source_path_mismatch:{decision['source_path']}")
    if rule["source_hash"] != decision["source_hash"]:
        issues.append(f"rule_source_hash_mismatch:{decision['source_path']}")
    if rule["source_anchor"] != decision["source_anchor"]:
        issues.append(f"rule_source_anchor_mismatch:{decision['source_path']}")
    if rule["domain"] not in decision["domains"]:
        issues.append(f"rule_domain_mismatch:{decision['source_path']}")
    if rule["language"] not in decision["languages"]:
        issues.append(f"rule_language_mismatch:{decision['source_path']}")
    if decision["source_hash"] == "sha256:missing":
        issues.append(f"source_hash_missing:{decision['source_path']}")
    elif not _is_sha256(decision["source_hash"]):
        issues.append(f"source_hash_invalid:{decision['source_path']}")
    if not decision["source_anchor"]:
        issues.append(f"missing_source_anchor:{decision['source_path']}")
    if not decision["source_anchor_policy"]:
        issues.append(f"missing_source_anchor_policy:{decision['source_path']}")
    return issues


def _non_executable_issues(decision: dict[str, Any]) -> list[str]:
    rule = decision["rule_decision"]
    issues: list[str] = []
    if not rule["non_blocking"]:
        issues.append(f"non_executable_blocks:{decision['source_path']}")
    if rule["kind"] != "excluded" and not rule["missing_capability"]:
        issues.append(f"missing_capability:{decision['source_path']}")
    if not rule["non_blocking_behavior"]:
        issues.append(f"missing_non_blocking_behavior:{decision['source_path']}")
    if rule["kind"] == "advisory" and not rule["review_guidance"]:
        issues.append(f"missing_review_guidance:{decision['source_path']}")
    if rule["kind"] == "non-executable" and not rule["manual_review_surface"]:
        issues.append(f"missing_manual_review_surface:{decision['source_path']}")
    if rule["kind"] == "unsupported" and not rule["future_backend_candidate"]:
        issues.append(f"missing_future_backend_candidate:{decision['source_path']}")
    if rule["kind"] in {"advisory", "non-executable", "unsupported"}:
        if rule["rule_ids"]:
            issues.append(f"non_executable_has_rule_ids:{decision['source_path']}")
        if rule["backend_ids"] or rule["detector_ids"]:
            issues.append(f"non_executable_has_backend:{decision['source_path']}")
        if rule["fixture_families"] or rule["test_ids"]:
            issues.append(f"non_executable_has_tests:{decision['source_path']}")
    return issues


def _generated_executable_issues(decision: dict[str, Any]) -> list[str]:
    rule = decision["rule_decision"]
    issues: list[str] = []
    if not rule["generator_id"] or not rule["generator_version"]:
        issues.append(f"missing_generator:{decision['source_path']}")
    if not rule["input_source_hashes"]:
        issues.append(f"missing_generator_input_hashes:{decision['source_path']}")
    if not rule["generated_catalog_snapshot"]:
        issues.append(f"missing_generated_catalog_snapshot:{decision['source_path']}")
    return issues


def _excluded_issues(excluded: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if excluded["source_hash"] == "sha256:missing":
        issues.append(f"source_hash_missing:{excluded['source_path']}")
    elif not _is_sha256(excluded["source_hash"]):
        issues.append(f"source_hash_invalid:{excluded['source_path']}")
    if excluded["rule_decision"]["kind"] != "excluded":
        issues.append(f"excluded_kind_mismatch:{excluded['source_path']}")
    if not excluded["rule_decision"]["reason"]:
        issues.append(f"excluded_reason_missing:{excluded['source_path']}")
    return issues


def _is_sha256(value: str) -> bool:
    digest = value.removeprefix("sha256:")
    return (
        value.startswith("sha256:")
        and len(digest) == 64
        and all(char in "0123456789abcdef" for char in digest)
    )

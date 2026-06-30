# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""Decision builders for ARS source enforcement manifests."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import cast

from validator.conventions_gates import DEFAULT_AST_CATALOGS

from .ars_rules import ArsExecutableRule
from .catalog import AstCatalogError, load_ast_catalogs
from .corpus import SourceClassification
from .models import AstRule
from .source_decision_ars import generated_rule_fields, source_rules_for
from .source_decision_paths import anchor_policy, source_anchor, source_hash
from .source_decision_types import (
    ExcludedDecision,
    RuleDecision,
    SourceDecision,
    SourceDecisionKind,
)
from .source_family_checks import SourceFamilyCheck, family_for_source

NOTION_DEFERRED_TASK_ID = "38fb8415-08de-8130-99a9-eff9a1cf5283"


def build_source_decision(
    root: Path,
    source: SourceClassification,
    executable_rules: dict[str, list[dict[str, object]]],
    project_root: Path | None = None,
) -> SourceDecision:
    """Return the complete decision record for one classified source."""
    rel = source["path"]
    source_path = f"ai-ressources/{rel}"
    source_hash_value = source_hash(root, rel)
    source_file = root / rel
    decision = build_rule_decision(
        source,
        decision_kind(source, executable_rules.get(rel, [])),
        executable_rules.get(rel, []),
        project_root=project_root or Path.cwd(),
        source_path=source_path,
        source_hash=source_hash_value,
        source_anchor_policy=anchor_policy(source_file),
        source_anchor=source_anchor(source_file),
    )
    return _source_payload(source, source_path, source_hash_value, decision)


def _source_payload(
    source: SourceClassification,
    source_path: str,
    source_hash: str,
    decision: RuleDecision,
) -> SourceDecision:
    return {
        "source_id": source_path,
        "source_path": source_path,
        "source_hash": source_hash,
        "source_anchor_policy": decision["source_anchor_policy"],
        "source_anchor": decision["source_anchor"],
        "domains": source["domains"],
        "languages": source["languages"],
        "classification": {
            "support_class": source["support_status"],
            "support_reason": source["support_reason"],
        },
        "rule_decision": decision,
    }


def build_excluded_decision(root: Path, item: object) -> ExcludedDecision:
    """Return the inventory decision for one explicitly excluded source."""
    data = cast(dict[str, str], item)
    source_path = f"ai-ressources/{data['path']}"
    source_hash_value = source_hash(root, data["path"])
    return {
        "source_id": source_path,
        "source_path": source_path,
        "source_hash": source_hash_value,
        "rule_decision": _excluded_rule_decision(data, source_path, source_hash_value),
    }


def _excluded_rule_decision(
    data: dict[str, str], source_path: str, source_hash: str
) -> RuleDecision:
    return cast(
        RuleDecision,
        {
            **_shared_decision_fields(
                "excluded",
                source_path,
                source_hash,
                "excluded",
                "excluded",
                "excluded",
                "language-agnostic",
            ),
            "decision_id": f"excluded:{data['path']}",
            "reason": data["reason"],
            "decision_anchor": "manifest.exclusions",
            "missing_capability": "",
            "future_backend_candidate": "",
            "review_guidance": "",
            "manual_review_surface": "",
            "rule_ids": ["source.excluded"],
            **_empty_rule_evidence(non_blocking=True),
            "non_blocking_behavior": "Excluded from feature 073 inventory completeness only.",
        },
    )


def build_rule_decision(
    source: SourceClassification,
    kind: SourceDecisionKind,
    rules: list[dict[str, object]],
    *,
    project_root: Path,
    source_path: str,
    source_hash: str,
    source_anchor_policy: str,
    source_anchor: str,
) -> RuleDecision:
    """Return the nested rule decision for one source decision."""
    domain = source["domains"][0] if source["domains"] else "source"
    language = source["languages"][0] if source["languages"] else "language-agnostic"
    if rules:
        return _executable_rule_decision(
            source, kind, rules, source_path, source_hash, source_anchor_policy, source_anchor
        )
    if kind == "generated-executable":
        family = family_for_source(source["domains"], source["languages"], source_path)
        source_rules = source_rules_for(project_root, source["path"])
        return _generated_rule_decision(
            source,
            family,
            source_rules,
            source_path,
            source_hash,
            source_anchor_policy,
            source_anchor,
            domain,
            language,
        )
    return _non_blocking_rule_decision(
        source,
        kind,
        source_path,
        source_hash,
        source_anchor_policy,
        source_anchor,
        domain,
        language,
    )


def _executable_rule_decision(
    source: SourceClassification,
    kind: SourceDecisionKind,
    rules: list[dict[str, object]],
    source_path: str,
    source_hash: str,
    source_anchor_policy: str,
    source_anchor: str,
) -> RuleDecision:
    domain = source["domains"][0] if source["domains"] else "source"
    language = source["languages"][0] if source["languages"] else "language-agnostic"
    first = rules[0]
    return cast(
        RuleDecision,
        {
            **_shared_decision_fields(
                kind,
                source_path,
                source_hash,
                source_anchor_policy,
                source_anchor,
                domain,
                language,
            ),
            "decision_id": f"executable:{source['path']}",
            "reason": _anchored_reason(source["support_reason"], source_path, source_anchor),
            "decision_anchor": str(first["source_anchor"]),
            "missing_capability": "",
            "future_backend_candidate": "",
            "review_guidance": "",
            "manual_review_surface": "",
            "rule_ids": [str(rule["id"]) for rule in rules],
            "backend_ids": sorted({str(rule["backend"]) for rule in rules}),
            "detector_ids": [str(rule["detector"]) for rule in rules],
            "fixture_families": [str(rule["fixture_family"]) for rule in rules],
            "test_ids": [str(rule["test_id"]) for rule in rules],
            "deterministic_test_evidence": [
                cast(dict[str, str], rule["deterministic_test_evidence"]) for rule in rules
            ],
            **_generated_fields(),
            "non_blocking": False,
            "non_blocking_behavior": "",
        },
    )


def _generated_rule_decision(
    source: SourceClassification,
    family: SourceFamilyCheck,
    source_rules: list[ArsExecutableRule],
    source_path: str,
    source_hash: str,
    source_anchor_policy: str,
    source_anchor: str,
    domain: str,
    language: str,
) -> RuleDecision:
    return cast(
        RuleDecision,
        {
            **_shared_decision_fields(
                "generated-executable",
                source_path,
                source_hash,
                source_anchor_policy,
                source_anchor,
                domain,
                language,
            ),
            "decision_id": f"generated-executable:{source['path']}",
            "reason": _anchored_reason(_generated_reason(family), source_path, source_anchor),
            "decision_anchor": family.backend_id,
            "missing_capability": "",
            "future_backend_candidate": "",
            "review_guidance": "",
            "manual_review_surface": "",
            **generated_rule_fields(source, family, source_rules),
            "non_blocking": False,
            "non_blocking_behavior": "",
            "generator_id": f"source-family-generator:{family.family_id}",
            "generator_version": "1",
            "input_source_hashes": [source_hash],
            "generated_catalog_snapshot": f"source-family:{family.family_id}:{source_hash}",
        },
    )


def _non_blocking_rule_decision(
    source: SourceClassification,
    kind: SourceDecisionKind,
    source_path: str,
    source_hash: str,
    source_anchor_policy: str,
    source_anchor: str,
    domain: str,
    language: str,
) -> RuleDecision:
    kind_fields = _non_blocking_kind_fields(kind, domain, language)
    return cast(
        RuleDecision,
        {
            **_shared_decision_fields(
                kind,
                source_path,
                source_hash,
                source_anchor_policy,
                source_anchor,
                domain,
                language,
            ),
            "decision_id": f"{kind}:{source['path']}",
            "reason": _anchored_reason(
                _non_executable_reason(source, kind), source_path, source_anchor
            ),
            "decision_anchor": "source-classification",
            "missing_capability": _missing_capability(source, kind),
            **kind_fields,
            "rule_ids": _non_blocking_rule_ids(kind),
            **_empty_rule_evidence(non_blocking=True),
            "non_blocking_behavior": (
                "Visible in JSON/receipts and never emitted as a blocking gate violation."
            ),
        },
    )


def decision_kind(
    source: SourceClassification, rules: list[dict[str, object]]
) -> SourceDecisionKind:
    """Return executable/generated/deferred decision kind for one source."""
    if rules:
        return "executable"
    if _is_deferred_conceptual_editorial(source):
        return "deferred_conceptual_editorial"
    return "generated-executable"


def _is_deferred_conceptual_editorial(source: SourceClassification) -> bool:
    domains = set(source["domains"])
    languages = set(source["languages"])
    conceptual_domains = {"architecture", "copywriting", "legal", "pricing", "seo"}
    executable_signals = {
        "css",
        "delphi",
        "go",
        "javascript",
        "kotlin",
        "python",
        "rust",
        "shell",
        "sql",
        "swift",
        "typescript",
    }
    return bool(domains & conceptual_domains) and not bool(languages & executable_signals)


def _non_executable_reason(source: SourceClassification, kind: SourceDecisionKind) -> str:
    if kind == "deferred_conceptual_editorial":
        return (
            "Source is conceptual or editorial and is deferred to Project Notion task "
            f"{NOTION_DEFERRED_TASK_ID}; it is not counted as completed by this "
            "immediate executable remediation."
        )
    return source["support_reason"]


def _missing_capability(source: SourceClassification, kind: SourceDecisionKind) -> str:
    if kind == "deferred_conceptual_editorial":
        return f"deferred-conceptual-editorial:{NOTION_DEFERRED_TASK_ID}"
    return "semantic-runtime-visual-or-provider-detector"


def _non_blocking_kind_fields(
    kind: SourceDecisionKind, domain: str, language: str
) -> dict[str, str]:
    if kind == "deferred_conceptual_editorial":
        return _deferred_kind_fields()
    if kind == "advisory":
        return {
            "review_guidance": f"Review {domain} guidance manually when it is touched.",
            "manual_review_surface": "",
            "future_backend_candidate": "",
        }
    if kind == "non-executable":
        return {
            "review_guidance": "",
            "manual_review_surface": f"{domain} prose/product review",
            "future_backend_candidate": "",
        }
    return {
        "review_guidance": "",
        "manual_review_surface": "",
        "future_backend_candidate": _future_backend_candidate(language, domain),
    }


def _deferred_kind_fields() -> dict[str, str]:
    return {
        "review_guidance": "",
        "manual_review_surface": (
            f"Project Notion task {NOTION_DEFERRED_TASK_ID} executable obligation checks"
        ),
        "future_backend_candidate": "conceptual_editorial_obligation_checker",
    }


def executable_rules_by_source(
    project_root: Path,
) -> tuple[dict[str, list[dict[str, object]]], list[str]]:
    """Return executable catalog rule metadata keyed by AI-res relative source."""
    by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
    try:
        catalogs = load_ast_catalogs(list(DEFAULT_AST_CATALOGS), project_root=project_root)
    except AstCatalogError as exc:
        return {}, [str(exc)]
    for catalog in catalogs:
        for rule in catalog.rules:
            by_source[rule.source_path.removeprefix("ai-ressources/")].append(
                _catalog_rule_payload(rule)
            )
    return by_source, []


def _catalog_rule_payload(rule: AstRule) -> dict[str, object]:
    family = _fixture_family(rule.fixtures.fail_path)
    return {
        "id": rule.id,
        "domain": rule.domain,
        "decision_kind": rule.decision_kind,
        "backend": rule.backend,
        "detector": rule.detector,
        "fixture_family": family,
        "source_hash": rule.source_hash,
        "source_anchor": rule.source_anchor,
        "test_id": f"pytest:tests/fixtures/conventions_ast/{family}",
        "deterministic_test_evidence": _catalog_test_evidence(rule),
    }


def _catalog_test_evidence(rule: AstRule) -> dict[str, str]:
    return {
        "test": "tests/test_conventions_ast_multilang.py",
        "pass_fixture": rule.fixtures.pass_path,
        "fail_fixture": rule.fixtures.fail_path,
    }


def _shared_decision_fields(
    kind: SourceDecisionKind,
    source_path: str,
    source_hash: str,
    source_anchor_policy: str,
    source_anchor: str,
    domain: str,
    language: str,
) -> dict[str, object]:
    return {
        "decision_kind": kind,
        "kind": kind,
        "source_path": source_path,
        "source_hash": source_hash,
        "source_anchor_policy": source_anchor_policy,
        "source_anchor": source_anchor,
        "domain": domain,
        "language": language,
    }


def _empty_rule_evidence(*, non_blocking: bool) -> dict[str, object]:
    return {
        "backend_ids": [],
        "detector_ids": [],
        "fixture_families": [],
        "test_ids": [],
        "deterministic_test_evidence": [],
        **_generated_fields(),
        "non_blocking": non_blocking,
    }


def _generated_fields() -> dict[str, object]:
    return {
        "generator_id": "",
        "generator_version": "",
        "input_source_hashes": [],
        "generated_catalog_snapshot": "",
    }


def _generated_reason(family: SourceFamilyCheck) -> str:
    return (
        f"Immediate-scope source is enforced by generated family {family.family_id}: "
        f"{family.description}"
    )


def _anchored_reason(reason: str, source_path: str, source_anchor: str) -> str:
    return f"{reason} Source decision anchored at {source_path}{source_anchor}."


def _non_blocking_rule_ids(kind: SourceDecisionKind) -> list[str]:
    if kind == "deferred_conceptual_editorial":
        return ["source.deferred_conceptual_editorial"]
    return []


def _future_backend_candidate(language: str, domain: str) -> str:
    if language == "css" or domain.startswith("design"):
        return "css_or_design_token_parser"
    if language == "sql" or domain == "database":
        return "sql_parser_or_bounded_sql_matcher"
    return "source_backed_deterministic_backend"


def _fixture_family(fail_path: str) -> str:
    parts = Path(fail_path).parts
    if "conventions_ast" not in parts:
        return str(Path(fail_path).parent)
    index = parts.index("conventions_ast")
    return Path(*parts[index + 1 : -1]).as_posix()

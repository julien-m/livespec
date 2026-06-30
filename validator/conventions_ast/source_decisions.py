# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""Per-source enforcement decisions for the AI-res/ARS convention corpus."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import cast

from validator.conventions_gates import DEFAULT_AST_CATALOGS
from validator.visual_evidence import sha256_file

from .catalog import AstCatalogError, load_ast_catalogs
from .corpus import SourceClassification, ai_resources_root, build_corpus_manifest
from .source_decision_types import (
    ExcludedDecision,
    RuleDecision,
    RuleDecisionManifest,
    SourceDecision,
    SourceDecisionKind,
)
from .source_decision_validation import validate_rule_decision_manifest as _validate_manifest


def build_rule_decision_manifest(project_root: Path) -> RuleDecisionManifest:
    """Return one explicit decision per classified AI-res/ARS source."""
    corpus = build_corpus_manifest(project_root)
    root = ai_resources_root(project_root)
    executable_rules, catalog_errors = _executable_rules_by_source(project_root)
    decisions = [
        _source_decision(root, source, executable_rules)
        for source in cast(list[SourceClassification], corpus["sources"])
    ]
    excluded = [_excluded_decision(root, item) for item in corpus["excluded_sources"]]
    undecided = _undecided_sources(decisions)
    counts = Counter(decision["rule_decision"]["kind"] for decision in decisions)
    return _manifest_payload(corpus, decisions, excluded, undecided, counts, catalog_errors)


def _undecided_sources(decisions: list[SourceDecision]) -> list[str]:
    return [
        decision["source_path"]
        for decision in decisions
        if not decision["rule_decision"]["decision_id"]
    ]


def _manifest_payload(
    corpus: object,
    decisions: list[SourceDecision],
    excluded: list[ExcludedDecision],
    undecided: list[str],
    counts: Counter[str],
    catalog_errors: list[str],
) -> RuleDecisionManifest:
    corpus_data = cast(dict[str, object], corpus)
    return {
        "total_source_count": cast(int, corpus_data["total_source_count"]),
        "decided_source_count": len(decisions) - len(undecided),
        "undecided_source_count": len(undecided),
        "executable_source_count": counts["executable"],
        "generated_executable_source_count": counts["generated-executable"],
        "advisory_source_count": counts["advisory"],
        "non_executable_source_count": counts["non-executable"],
        "unsupported_source_count": counts["unsupported"],
        "excluded_source_count": cast(int, corpus_data["excluded_count"]),
        "decision_kind_counts": dict(sorted(counts.items())),
        "catalog_load_errors": catalog_errors,
        "decisions": decisions,
        "undecided_sources": undecided,
        "excluded_sources": excluded,
    }


def validate_rule_decision_manifest(manifest: RuleDecisionManifest) -> list[str]:
    """Return blocking decision-manifest defects."""
    return _validate_manifest(cast(dict[str, object], manifest))


def _source_decision(
    root: Path,
    source: SourceClassification,
    executable_rules: dict[str, list[dict[str, object]]],
) -> SourceDecision:
    rel = source["path"]
    source_path = f"ai-ressources/{rel}"
    rules = executable_rules.get(rel, [])
    kind = _decision_kind(source, rules)
    source_hash = _source_hash(root, rel)
    source_anchor_policy = _anchor_policy(root / rel)
    source_anchor = _source_anchor(root / rel)
    decision = _rule_decision(
        source,
        kind,
        rules,
        source_path=source_path,
        source_hash=source_hash,
        source_anchor_policy=source_anchor_policy,
        source_anchor=source_anchor,
    )
    return {
        "source_id": source_path,
        "source_path": source_path,
        "source_hash": source_hash,
        "source_anchor_policy": source_anchor_policy,
        "source_anchor": source_anchor,
        "domains": source["domains"],
        "languages": source["languages"],
        "classification": {
            "support_class": source["support_status"],
            "support_reason": source["support_reason"],
        },
        "rule_decision": decision,
    }


def _excluded_decision(root: Path, item: object) -> ExcludedDecision:
    data = cast(dict[str, str], item)
    source_path = f"ai-ressources/{data['path']}"
    source_hash = _source_hash(root, data["path"])
    return {
        "source_id": source_path,
        "source_path": source_path,
        "source_hash": source_hash,
        "rule_decision": {
            "decision_id": f"excluded:{data['path']}",
            "decision_kind": "excluded",
            "kind": "excluded",
            "reason": data["reason"],
            "decision_anchor": "manifest.exclusions",
            "source_path": source_path,
            "source_hash": source_hash,
            "source_anchor_policy": "excluded",
            "source_anchor": "excluded",
            "domain": "excluded",
            "language": "language-agnostic",
            "missing_capability": "",
            "future_backend_candidate": "",
            "review_guidance": "",
            "manual_review_surface": "",
            "rule_ids": ["source.excluded"],
            "backend_ids": [],
            "detector_ids": [],
            "fixture_families": [],
            "test_ids": [],
            "deterministic_test_evidence": [],
            "non_blocking": True,
            "non_blocking_behavior": "Excluded from feature 073 inventory completeness only.",
            "generator_id": "",
            "generator_version": "",
            "input_source_hashes": [],
            "generated_catalog_snapshot": "",
        },
    }


def _rule_decision(
    source: SourceClassification,
    kind: SourceDecisionKind,
    rules: list[dict[str, object]],
    *,
    source_path: str,
    source_hash: str,
    source_anchor_policy: str,
    source_anchor: str,
) -> RuleDecision:
    domain = source["domains"][0] if source["domains"] else "source"
    language = source["languages"][0] if source["languages"] else "language-agnostic"
    if rules:
        return _executable_rule_decision(
            source,
            kind,
            rules,
            source_path,
            source_hash,
            source_anchor_policy,
            source_anchor,
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
    return {
        **_shared_decision_fields(
            kind, source_path, source_hash, source_anchor_policy, source_anchor, domain, language
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
        "non_blocking": False,
        "non_blocking_behavior": "",
        "generator_id": "",
        "generator_version": "",
        "input_source_hashes": [],
        "generated_catalog_snapshot": "",
    }


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
    kind_fields = _non_blocking_kind_fields(source, kind)
    return {
        **_shared_decision_fields(
            kind, source_path, source_hash, source_anchor_policy, source_anchor, domain, language
        ),
        "decision_id": f"{kind}:{source['path']}",
        "reason": _anchored_reason(
            _non_executable_reason(source, kind), source_path, source_anchor
        ),
        "decision_anchor": "source-classification",
        "missing_capability": _missing_capability(source, kind),
        "future_backend_candidate": kind_fields["future_backend_candidate"],
        "review_guidance": kind_fields["review_guidance"],
        "manual_review_surface": kind_fields["manual_review_surface"],
        "rule_ids": [],
        "backend_ids": [],
        "detector_ids": [],
        "fixture_families": [],
        "test_ids": [],
        "deterministic_test_evidence": [],
        "non_blocking": True,
        "non_blocking_behavior": (
            "Visible in JSON/receipts and never emitted as a blocking gate violation."
        ),
        "generator_id": "",
        "generator_version": "",
        "input_source_hashes": [],
        "generated_catalog_snapshot": "",
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


def _decision_kind(
    source: SourceClassification,
    rules: list[dict[str, object]],
) -> SourceDecisionKind:
    if rules:
        return "executable"
    domains = set(source["domains"])
    languages = set(source["languages"])
    if domains & {"legal", "copywriting", "pricing"}:
        return "non-executable"
    if languages & {"css", "delphi", "go", "python", "shell", "sql"}:
        return "unsupported"
    if source["support_status"] == "unsupported":
        return "unsupported"
    return "advisory"


def _non_executable_reason(source: SourceClassification, kind: SourceDecisionKind) -> str:
    if kind == "non-executable":
        return (
            "Source is prose, product, legal, copy, or pricing guidance; it is visible "
            "for review but cannot safely block deterministic verification."
        )
    if kind == "unsupported":
        return (
            "Source may contain enforceable guidance, but no complete backend, detector, "
            "fixtures, and tests are available for this language/domain yet."
        )
    return source["support_reason"]


def _anchored_reason(reason: str, source_path: str, source_anchor: str) -> str:
    return f"{reason} Source decision anchored at {source_path}{source_anchor}."


def _missing_capability(source: SourceClassification, kind: SourceDecisionKind) -> str:
    if kind == "non-executable":
        return "deterministic-oracle"
    if kind == "unsupported":
        languages = ",".join(source["languages"]) or "language"
        return f"backend-detector-fixtures-tests:{languages}"
    return "semantic-runtime-visual-or-provider-detector"


def _non_blocking_kind_fields(
    source: SourceClassification,
    kind: SourceDecisionKind,
) -> dict[str, str]:
    domain = source["domains"][0] if source["domains"] else "source"
    language = source["languages"][0] if source["languages"] else "language-agnostic"
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
    if kind == "unsupported":
        return {
            "review_guidance": "",
            "manual_review_surface": "",
            "future_backend_candidate": _future_backend_candidate(language, domain),
        }
    return {"review_guidance": "", "manual_review_surface": "", "future_backend_candidate": ""}


def _future_backend_candidate(language: str, domain: str) -> str:
    if language == "css" or domain.startswith("design"):
        return "css_or_design_token_parser"
    if language == "sql" or domain == "database":
        return "sql_parser_or_bounded_sql_matcher"
    if language in {"delphi", "go", "python", "shell"}:
        return f"{language}_ast_or_static_analysis_backend"
    return "source_backed_deterministic_backend"


def _executable_rules_by_source(
    project_root: Path,
) -> tuple[dict[str, list[dict[str, object]]], list[str]]:
    by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
    try:
        catalogs = load_ast_catalogs(list(DEFAULT_AST_CATALOGS), project_root=project_root)
    except AstCatalogError as exc:
        return {}, [str(exc)]
    for catalog in catalogs:
        for rule in catalog.rules:
            rel = rule.source_path.removeprefix("ai-ressources/")
            family = _fixture_family(rule.fixtures.fail_path)
            by_source[rel].append(
                {
                    "id": rule.id,
                    "domain": rule.domain,
                    "decision_kind": rule.decision_kind,
                    "backend": rule.backend,
                    "detector": rule.detector,
                    "fixture_family": family,
                    "source_hash": rule.source_hash,
                    "source_anchor": rule.source_anchor,
                    "test_id": f"pytest:tests/fixtures/conventions_ast/{family}",
                    "deterministic_test_evidence": {
                        "test": "tests/test_conventions_ast_multilang.py",
                        "pass_fixture": rule.fixtures.pass_path,
                        "fail_fixture": rule.fixtures.fail_path,
                    },
                }
            )
    return by_source, []


def _fixture_family(fail_path: str) -> str:
    parts = Path(fail_path).parts
    try:
        index = parts.index("conventions_ast")
    except ValueError:
        return str(Path(fail_path).parent)
    return Path(*parts[index + 1 : -1]).as_posix()


def _source_hash(root: Path, rel: str) -> str:
    source_file = root / rel
    if not source_file.is_file():
        return "sha256:missing"
    return f"sha256:{sha256_file(source_file)}"


def _anchor_policy(source_file: Path) -> str:
    return "yaml-key-path" if source_file.suffix in {".yaml", ".yml"} else "heading-or-line-range"


def _source_anchor(source_file: Path) -> str:
    if source_file.suffix in {".yaml", ".yml"}:
        return "$"
    try:
        for line in source_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                return _markdown_anchor(line)
    except OSError:
        return "line:1"
    return "line:1"


def _markdown_anchor(line: str) -> str:
    title = line.lstrip("#").strip().lower()
    slug = "".join(char if char.isalnum() or char in " -" else "" for char in title)
    return "#" + "-".join(slug.split())

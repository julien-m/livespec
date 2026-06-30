# @spec FR-008, FR-009: Exhaustive AI-res conventions manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""AI-resources convention corpus discovery and classification.

This module is intentionally deterministic: it classifies source files by
repository path and conservative filename signals, then reports every excluded
or unsupported source explicitly. The invariant for feature 073 is that every
in-scope AI-res/ARS convention source is either classified or excluded with a
reason; there is no silent drop path.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TypedDict

import yaml


class SourceClassification(TypedDict):
    """One classified AI-res source file."""

    path: str
    domains: list[str]
    languages: list[str]
    support_status: str
    support_reason: str


class ExcludedSource(TypedDict):
    """One intentionally excluded AI-res file."""

    path: str
    reason: str


class CorpusManifest(TypedDict):
    """Machine-readable corpus completeness report."""

    ai_resources_root: str
    total_source_count: int
    classified_count: int
    unclassified_count: int
    excluded_count: int
    sources: list[SourceClassification]
    unclassified_sources: list[str]
    excluded_sources: list[ExcludedSource]
    language_domain_matrix: dict[str, list[str]]
    domain_source_counts: dict[str, int]


_SOURCE_SUFFIXES = {".md", ".yaml", ".yml"}
_SKIP_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".claude",
    ".agent-sync",
    ".agent-sync.local",
    "node_modules",
    "schemas",
    "scripts",
}
_SKIP_FILES = {
    ".DS_Store",
    ".editorconfig",
    ".gitignore",
    ".last-updated",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "README.md",
    "bun.lock",
    "package.json",
    "compiled-index.txt",
    "setup.sh",
}
_IN_SCOPE_TOP_LEVEL = {
    "architecture",
    "code-conventions",
    "conventions",
    "copywriting",
    "design",
    "docs",
    "legal",
    "models",
    "pricing-models",
    "seo",
    "stack-ref",
}
_IN_SCOPE_ROOT_FILES = {"domain-catalog.md", "index.yaml"}
_ENFORCED_AST_SOURCES = {
    "code-conventions/javascript.md",
    "code-conventions/rust.md",
    "code-conventions/swift-kotlin.md",
}
_SUPPORTED_LANGUAGE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("typescript", ("typescript", "ts", "tsx", "nextjs", "react", "astro", "tanstack", "shadcn")),
    ("javascript", ("javascript", "js", "jsx", "node", "remotion")),
    ("python", ("python", "py", "ruff", "pyright")),
    ("rust", ("rust", "cargo")),
    ("go", ("go", "golang")),
    ("swift", ("swift", "ios", "xcuitest")),
    ("kotlin", ("kotlin", "android", "ktlint", "detekt")),
    ("sql", ("sql", "database", "databases", "postgres", "mysql", "sqlite", "drizzle", "prisma")),
    ("css", ("css", "tailwind", "tokens", "spacing", "colors", "typography")),
    ("shell", ("cli", "shell", "bash")),
    ("delphi", ("delphi",)),
)


def ai_resources_root(project_root: Path | None = None) -> Path:
    """Return the configured AI-resources root for a LiveSpec project."""
    if project_root is None:
        return Path.home() / "projects" / "ai-ressources"
    manifest = project_root / ".conventions" / "manifest.yaml"
    try:
        raw: object = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return Path.home() / "projects" / "ai-ressources"
    if isinstance(raw, dict) and isinstance(raw.get("ai_resources_path"), str):
        return Path(raw["ai_resources_path"])
    return Path.home() / "projects" / "ai-ressources"


def build_corpus_manifest(project_root: Path) -> CorpusManifest:
    """Build an exhaustive source classification manifest for AI-resources."""
    root = ai_resources_root(project_root)
    if not root.is_dir():
        return _empty_manifest(root)
    classified, unclassified, excluded = _scan_corpus_sources(root)
    total_sources = len(classified) + len(unclassified)
    return {
        "ai_resources_root": root.as_posix(),
        "total_source_count": total_sources,
        "classified_count": len(classified),
        "unclassified_count": len(unclassified),
        "excluded_count": len(excluded),
        "sources": classified,
        "unclassified_sources": unclassified,
        "excluded_sources": excluded,
        "language_domain_matrix": _language_domain_matrix(classified),
        "domain_source_counts": _domain_counts(classified),
    }


def _empty_manifest(root: Path) -> CorpusManifest:
    return {
        "ai_resources_root": root.as_posix(),
        "total_source_count": 0,
        "classified_count": 0,
        "unclassified_count": 0,
        "excluded_count": 0,
        "sources": [],
        "unclassified_sources": [],
        "excluded_sources": [],
        "language_domain_matrix": {},
        "domain_source_counts": {},
    }


def _scan_corpus_sources(
    root: Path,
) -> tuple[list[SourceClassification], list[str], list[ExcludedSource]]:
    classified: list[SourceClassification] = []
    unclassified: list[str] = []
    excluded: list[ExcludedSource] = []
    for source_path in sorted(path for path in root.rglob("*") if path.is_file()):
        rel = source_path.relative_to(root).as_posix()
        if source_path.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        exclusion_reason = _exclusion_reason(rel, source_path)
        if exclusion_reason is not None:
            excluded.append({"path": rel, "reason": exclusion_reason})
            continue
        item = classify_source(rel)
        if item is None:
            unclassified.append(rel)
        else:
            classified.append(item)
    return classified, unclassified, excluded


def classify_source(rel: str) -> SourceClassification | None:
    """Classify one AI-res relative source path, or return None if unknown."""
    parts = rel.split("/")
    top = parts[0]
    if top not in _IN_SCOPE_TOP_LEVEL and rel not in _IN_SCOPE_ROOT_FILES:
        return None
    domains = _domains_for(rel, parts)
    languages = _languages_for(rel)
    if not domains:
        return None
    status, reason = _support_for(rel, domains)
    return {
        "path": rel,
        "domains": sorted(domains),
        "languages": sorted(languages) if languages else ["language-agnostic"],
        "support_status": status,
        "support_reason": reason,
    }


def _exclusion_reason(rel: str, source_path: Path) -> str | None:
    parts = rel.split("/")
    if any(part in _SKIP_DIRS for part in parts[:-1]):
        return "tooling_or_generated_directory"
    if source_path.name in _SKIP_FILES:
        return "repository_governance_or_non_convention_file"
    if rel.startswith("templates/"):
        return "template_scaffold_not_source_convention"
    return None


def _domains_for(rel: str, parts: list[str]) -> set[str]:
    text = rel.lower().replace("-", "_")
    domains = _base_domains_for(rel, parts, text)
    domains.update(_keyword_domains_for(text))
    stem = Path(rel).stem.lower()
    if stem in {"testing", "logging", "runtime-configs", "stack-commands"}:
        domains.add("code")
    return domains


def _base_domains_for(rel: str, parts: list[str], text: str) -> set[str]:
    domains: set[str] = set()
    top = parts[0]
    if top in {"domain-catalog.md", "index.yaml"} or rel in _IN_SCOPE_ROOT_FILES:
        domains.add("catalog")
    if top == "architecture" or "architecture" in text:
        domains.add("architecture")
    if top == "code-conventions":
        domains.add("code")
    if top == "conventions":
        domains.add("conventions")
    if top == "copywriting":
        domains.add("copywriting")
    if top == "design":
        domains.add("design")
        if len(parts) > 2:
            domains.add(f"design-{parts[1]}")
    if top == "docs":
        domains.update(_docs_domains_for(text))
    if top == "legal":
        domains.add("legal")
    if top == "models":
        domains.add("ai")
    if top == "pricing-models":
        domains.add("pricing")
    if top == "seo":
        domains.update({"seo", "copywriting"})
    if top == "stack-ref":
        domains.update(_stack_domains_for(parts))
    return domains


def _docs_domains_for(text: str) -> set[str]:
    domains = {"code"}
    if "design" in text:
        domains.add("design")
    if "architecture" in text:
        domains.add("architecture")
    if any(marker in text for marker in ("convention", "testing", "ci", "precommit")):
        domains.add("conventions")
    return domains


def _stack_domains_for(parts: list[str]) -> set[str]:
    domains = {"stack"}
    if len(parts) > 2 and parts[1] != "_templates":
        mapped = {
            "databases": "database",
            "jobs": "jobs",
            "ops": "ops",
            "payments": "payment",
            "platforms": "platform",
        }.get(parts[1], parts[1])
        domains.add(mapped)
    return domains


def _keyword_domains_for(text: str) -> set[str]:
    domains: set[str] = set()
    if _has_database_signal(text):
        domains.add("database")
    if _has_payment_signal(text):
        domains.add("payment")
    if any(marker in text for marker in ("legal", "rgpd", "privacy", "cookie", "cgu", "cgv")):
        domains.add("legal")
    if _has_pricing_signal(text):
        domains.add("pricing")
    return domains


def _has_database_signal(text: str) -> bool:
    markers = ("database", "databases", "postgres", "mysql", "sqlite", "sql", "drizzle", "prisma")
    return any(marker in text for marker in markers)


def _has_payment_signal(text: str) -> bool:
    markers = (
        "payment",
        "payments",
        "stripe",
        "paddle",
        "mollie",
        "lemon_squeezy",
        "merchant_of_record",
    )
    return any(marker in text for marker in markers)


def _has_pricing_signal(text: str) -> bool:
    markers = ("pricing", "freemium", "usage_based", "per_seat", "flat_rate")
    return any(marker in text for marker in markers)


def _languages_for(rel: str) -> set[str]:
    text = rel.lower().replace("-", "_")
    languages: set[str] = set()
    for language, markers in _SUPPORTED_LANGUAGE_MARKERS:
        if any(marker in text for marker in markers):
            languages.add(language)
    if "swift_kotlin" in text:
        languages.update({"swift", "kotlin"})
    if "general" in text or "architecture" in text:
        languages.add("language-agnostic")
    return languages


def _support_for(rel: str, domains: set[str]) -> tuple[str, str]:
    if rel in _ENFORCED_AST_SOURCES:
        return (
            "enforced_ast",
            "At least one high-precision AST rule is sourced from this file; "
            "remaining guidance stays classified by support class.",
        )
    advisory_domains = {
        "code",
        "database",
        "design",
        "payment",
        "architecture",
        "seo",
        "stack",
        "conventions",
    }
    if domains & advisory_domains:
        return (
            "advisory",
            "Source is classified and surfaced, but full enforcement requires "
            "semantic, runtime, visual, or provider-specific detectors.",
        )
    return (
        "unsupported",
        "Source is prose/product guidance with no reliable AST detector; kept "
        "explicit so it is not silently treated as enforced.",
    )


def _language_domain_matrix(
    sources: list[SourceClassification],
) -> dict[str, list[str]]:
    matrix: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        for language in source["languages"]:
            matrix[language].update(source["domains"])
    return {language: sorted(domains) for language, domains in sorted(matrix.items())}


def _domain_counts(sources: list[SourceClassification]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for source in sources:
        for domain in source["domains"]:
            counts[domain] += 1
    return dict(sorted(counts.items()))

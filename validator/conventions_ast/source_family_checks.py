# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""Deterministic checker families for generated ARS source decisions."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFamilyCheck:
    """Executable fixture contract for a generated source family."""

    family_id: str
    rule_id: str
    backend_id: str
    detector_id: str
    fixture_family: str
    pass_fixture: str
    fail_fixture: str
    description: str
    check: Callable[[str], bool]


def evaluate_source_family_fixture(family_id: str, fixture_path: Path) -> list[str]:
    """Return detector IDs triggered by one source-family fixture."""
    family = SOURCE_FAMILY_CHECKS[family_id]
    text = fixture_path.read_text(encoding="utf-8")
    return [family.detector_id] if family.check(text) else []


def family_for_source(
    domains: list[str], languages: list[str], source_path: str
) -> SourceFamilyCheck:
    """Return the executable family that covers one immediate-scope source."""
    domain_set = set(domains)
    language_set = set(languages)
    path = source_path.lower()
    family_id = _family_id_for_source(domain_set, language_set, path)
    return SOURCE_FAMILY_CHECKS[family_id]


def _family_id_for_source(domains: set[str], languages: set[str], path: str) -> str:
    if "sql" in languages or "database" in domains:
        return "database_sql"
    if "payment" in domains:
        return "payment_contract"
    if "css" in languages or "design-tokens" in domains or "tailwind" in path:
        return "css_design_tokens"
    if "typescript" in languages:
        return "typescript_ui" if domains & {"design", "design-components"} else "javascript_code"
    if "javascript" in languages:
        return "javascript_code"
    if "python" in languages:
        return "ai_prompt" if "ai" in domains else "python_code"
    if "shell" in languages:
        return "shell_code"
    if "go" in languages:
        return "go_code"
    if "delphi" in languages:
        return "delphi_code"
    if domains & {"design", "design-components", "design-quality", "design-references"}:
        return "design_system"
    if domains & {
        "platform",
        "ops",
        "jobs",
        "frontend",
        "auth",
        "cms",
        "search",
        "storage",
        "stack",
    }:
        return "platform_ops"
    if domains & {"ai", "email"}:
        return "ai_prompt"
    if "code" in domains or "conventions" in domains:
        return "code_prose"
    if "catalog" in domains:
        return "markdown_docs" if path.endswith(".md") else "json_yaml_config"
    return "code_prose"


def _contains(pattern: str) -> Callable[[str], bool]:
    regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    return lambda text: bool(regex.search(text))


def _fixture(family_id: str, name: str) -> str:
    return f"tests/fixtures/conventions_ast/generated/{family_id}/{name}"


def _family(
    family_id: str,
    *,
    description: str,
    pattern: str,
    pass_name: str = "pass.txt",
    fail_name: str = "fail.txt",
    check: Callable[[str], bool] | None = None,
) -> SourceFamilyCheck:
    fixture_family = f"generated/{family_id}"
    return SourceFamilyCheck(
        family_id=family_id,
        rule_id=f"source_family.{family_id}",
        backend_id=f"source-family:{family_id}",
        detector_id=f"source-family.{family_id}.detector",
        fixture_family=fixture_family,
        pass_fixture=_fixture(family_id, pass_name),
        fail_fixture=_fixture(family_id, fail_name),
        description=description,
        check=check or _contains(pattern),
    )


SOURCE_FAMILY_CHECKS: dict[str, SourceFamilyCheck] = {
    "ai_prompt": _family(
        "ai_prompt",
        description="Prompts must avoid unsafe high-temperature defaults.",
        pattern=r"\btemperature\s*[:=]\s*(?:1\.[1-9]|[2-9])",
        pass_name="pass.yaml",
        fail_name="fail.yaml",
    ),
    "code_prose": _family(
        "code_prose",
        description="Code guidance must not permit untyped escape hatches.",
        pattern=r"\ballow\s+(?:any|object|untyped)\b",
    ),
    "css_design_tokens": _family(
        "css_design_tokens",
        description="CSS and Tailwind guidance must reject raw visual literals.",
        pattern=r"(?:#[0-9a-f]{3,8}\b|\b(?:m|p|gap|text|bg)-\[[^\]]+\])",
        pass_name="pass.css",
        fail_name="fail.css",
    ),
    "database_sql": _family(
        "database_sql",
        description="Database guidance must catch destructive or unbounded SQL.",
        pattern=r"\b(?:select\s+\*|drop\s+table|delete\s+from\s+\w+\s*;)",
        pass_name="pass.sql",
        fail_name="fail.sql",
    ),
    "delphi_code": _family(
        "delphi_code",
        description="Delphi guidance must catch empty exception handlers.",
        pattern=r"\bexcept\s*(?:\r?\n|\s)+end\s*;",
        pass_name="pass.pas",
        fail_name="fail.pas",
    ),
    "design_system": _family(
        "design_system",
        description="Design guidance must reject decorative one-off visual tokens.",
        pattern=r"\b(?:gradient orb|bokeh|border-radius:\s*999px)\b",
    ),
    "go_code": _family(
        "go_code",
        description="Go guidance must catch panic-driven control flow.",
        pattern=r"\bpanic\s*\(",
        pass_name="pass.go",
        fail_name="fail.go",
    ),
    "javascript_code": _family(
        "javascript_code",
        description="JS/TS guidance must reject CommonJS in ESM surfaces.",
        pattern=r"\brequire\s*\(",
        pass_name="pass.ts",
        fail_name="fail.ts",
    ),
    "json_yaml_config": _family(
        "json_yaml_config",
        description="Structured config guidance must reject inline secrets.",
        pattern=r"\b(?:password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_/-]{8,}",
        pass_name="pass.yaml",
        fail_name="fail.yaml",
    ),
    "markdown_docs": _family(
        "markdown_docs",
        description="Documentation guidance must reject unresolved placeholders.",
        pattern=r"\b(?:TODO|TBD|FIXME)\b",
        pass_name="pass.md",
        fail_name="fail.md",
    ),
    "payment_contract": _family(
        "payment_contract",
        description="Payment guidance must require idempotency/currency discipline.",
        pattern=r"\bamount\s*[:=]\s*\d+\b(?!.*\bcurrency\b)|webhook.*without idempotency",
        pass_name="pass.ts",
        fail_name="fail.ts",
        check=lambda text: (
            ("amount" in text and "currency" not in text)
            or bool(re.search(r"webhook.*without idempotency", text, re.IGNORECASE))
        ),
    ),
    "platform_ops": _family(
        "platform_ops",
        description="Platform guidance must reject floating latest versions.",
        pattern=r":latest\b|\blatest\s+version\b",
        pass_name="pass.yaml",
        fail_name="fail.yaml",
    ),
    "python_code": _family(
        "python_code",
        description="Python guidance must catch silently swallowed exceptions.",
        pattern=r"except\s+Exception\s*:\s*(?:pass|return\s+None)",
        pass_name="pass.py",
        fail_name="fail.py",
    ),
    "shell_code": _family(
        "shell_code",
        description="Shell guidance must reject pipe-to-shell installation.",
        pattern=r"curl\b.*\|\s*(?:sh|bash)",
        pass_name="pass.sh",
        fail_name="fail.sh",
    ),
    "typescript_ui": _family(
        "typescript_ui",
        description="UI guidance must catch interactive elements without test IDs.",
        pattern=r"<button(?![^>]*data-testid=)",
        pass_name="pass.tsx",
        fail_name="fail.tsx",
    ),
}

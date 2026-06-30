# @spec FR-015: Active ast/high catalogue
#   .specs/features/072-conventions-ast-rule-engine/spec.md#fr-015

"""AST rule catalogue loading and validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from validator.conventions_ast.models import (
    AstCatalog,
    AstDeterministicTestEvidence,
    AstFixtures,
    AstJustification,
    AstPattern,
    AstRule,
)
from validator.visual_evidence import sha256_file


class AstCatalogError(ValueError):
    """Raised when an AST catalogue is invalid."""


AST_RULE_DOMAINS = frozenset({"code"})


def load_ast_catalog(path: Path, *, project_root: Path) -> AstCatalog:
    """Load one AST rule catalogue and validate active v1 constraints."""
    catalog_path = _resolve_catalog_path(path, project_root)
    try:
        raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise AstCatalogError(f"catalog unreadable: {catalog_path}") from exc
    if not isinstance(raw, dict):
        raise AstCatalogError("catalog root must be a mapping")
    # PyYAML returns object-shaped mappings; validation below narrows keys and values.
    raw_data = cast(dict[str, Any], raw)
    rules_raw = raw_data.get("rules")
    if not isinstance(rules_raw, list):
        raise AstCatalogError("catalog rules must be a list")
    fixture_root = _fixture_root(catalog_path, project_root)
    rules = tuple(
        _parse_rule(item, project_root=project_root, fixture_root=fixture_root)
        for item in rules_raw
    )
    return AstCatalog(path=catalog_path, rules=rules, sha256=sha256_file(catalog_path))


def load_ast_catalogs(paths: list[str], *, project_root: Path) -> tuple[AstCatalog, ...]:
    """Load all configured AST catalogues."""
    return tuple(load_ast_catalog(Path(path), project_root=project_root) for path in paths)


def ast_catalogs_sha256(catalogs: tuple[AstCatalog, ...]) -> str:
    """Return a stable hash for active catalogue file and rule metadata."""
    import hashlib
    import json

    payload = [
        {
            "path": catalog.path.as_posix(),
            "sha256": catalog.sha256,
            "rules": [rule.metadata_payload() for rule in catalog.rules],
        }
        for catalog in catalogs
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _parse_rule(raw: object, *, project_root: Path, fixture_root: Path) -> AstRule:
    if not isinstance(raw, dict):
        raise AstCatalogError("catalog rule must be a mapping")
    # Rule entries are validated field-by-field before constructing typed models.
    data = cast(dict[str, Any], raw)
    decidability = _string(data, "decidability")
    precision = _string(data, "precision")
    if decidability != "ast" or precision != "high":
        raise AstCatalogError(
            "active v1 AST catalog accepts only decidability ast and precision high"
        )
    decision_kind = _string(data, "decision_kind")
    if decision_kind == "executable":
        typed_decision_kind: Literal["executable", "generated-executable"] = "executable"
    elif decision_kind == "generated-executable":
        typed_decision_kind = "generated-executable"
    else:
        raise AstCatalogError("decision_kind must be executable or generated-executable")
    detector = _string(data, "detector")
    rule_id = _string(data, "id")
    if detector != rule_id:
        raise AstCatalogError("detector must match rule id")
    domain = _string(data, "domain")
    if domain not in AST_RULE_DOMAINS:
        expected = ", ".join(sorted(AST_RULE_DOMAINS))
        raise AstCatalogError(f"domain must be one of: {expected}")
    fixtures = _fixtures(data, fixture_root)
    deterministic_test_evidence = _deterministic_test_evidence(data, fixtures, fixture_root)
    source_path = _string(data, "source_path")
    source_hash = _string(data, "source_hash")
    _validate_traceability(
        source_path,
        _string(data, "source_anchor"),
        source_hash,
        project_root=project_root,
    )
    patterns = tuple(_patterns(data))
    if not patterns:
        raise AstCatalogError("rule patterns must not be empty")
    return AstRule(
        id=rule_id,
        title=_string(data, "title"),
        language=_string(data, "language"),
        domain=domain,
        decision_kind=typed_decision_kind,
        decidability="ast",
        precision="high",
        severity=_severity(data),
        source_path=source_path,
        source_anchor=_string(data, "source_anchor"),
        source_hash=source_hash,
        backend=_string(data, "backend"),
        detector=detector,
        patterns=patterns,
        fixtures=fixtures,
        deterministic_test_evidence=deterministic_test_evidence,
        justification=_justification(data),
    )


def _resolve_catalog_path(path: Path, project_root: Path) -> Path:
    resolved = path if path.is_absolute() else project_root / path
    if resolved.is_file():
        return resolved
    bundled = _package_root() / path if not path.is_absolute() else resolved
    if bundled.is_file():
        return bundled
    raise AstCatalogError(f"catalog not found: {path}")


def _fixture_root(catalog_path: Path, project_root: Path) -> Path:
    try:
        catalog_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return _package_root()
    return project_root


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fixtures(data: dict[str, Any], fixture_root: Path) -> AstFixtures:
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, dict):
        raise AstCatalogError("rule fixtures must be a mapping")
    pass_path = _string(fixtures, "pass")
    fail_path = _string(fixtures, "fail")
    for fixture_path in (pass_path, fail_path):
        resolved = fixture_root / fixture_path
        if not resolved.is_file():
            raise AstCatalogError(f"fixture missing: {fixture_path}")
    return AstFixtures(pass_path=pass_path, fail_path=fail_path)


def _deterministic_test_evidence(
    data: dict[str, Any],
    fixtures: AstFixtures,
    fixture_root: Path,
) -> tuple[AstDeterministicTestEvidence, ...]:
    raw = data.get("deterministic_test_evidence")
    if not isinstance(raw, list) or not raw:
        raise AstCatalogError("deterministic_test_evidence must be a non-empty list")
    parsed: list[AstDeterministicTestEvidence] = []
    for item in raw:
        if not isinstance(item, dict):
            raise AstCatalogError("deterministic_test_evidence item must be a mapping")
        item_data = cast(dict[str, Any], item)
        test = _string(item_data, "test")
        pass_fixture = _string(item_data, "pass_fixture")
        fail_fixture = _string(item_data, "fail_fixture")
        if pass_fixture != fixtures.pass_path or fail_fixture != fixtures.fail_path:
            raise AstCatalogError("deterministic_test_evidence fixtures must match rule fixtures")
        if not (fixture_root / test).is_file():
            raise AstCatalogError(f"deterministic test missing: {test}")
        parsed.append(
            AstDeterministicTestEvidence(
                test=test,
                pass_fixture=pass_fixture,
                fail_fixture=fail_fixture,
            )
        )
    return tuple(parsed)


def _validate_traceability(
    source_path: str,
    source_anchor: str,
    source_hash: str,
    *,
    project_root: Path,
) -> None:
    if "ai-ressources/code-conventions" not in source_path:
        raise AstCatalogError("source_path must point to ai-ressources/code-conventions")
    if not source_anchor.startswith("#"):
        raise AstCatalogError("source_anchor must be a markdown anchor")
    if not source_hash.startswith("sha256:") or len(source_hash.removeprefix("sha256:")) != 64:
        raise AstCatalogError("source_hash must be sha256:<64 lowercase hex chars>")
    source_file = _resolve_source_path(source_path, project_root)
    if not source_file.is_file():
        raise AstCatalogError(f"source_path missing: {source_path}")
    if f"sha256:{sha256_file(source_file)}" != source_hash:
        raise AstCatalogError("source_hash mismatch")


def _resolve_source_path(source_path: str, project_root: Path) -> Path:
    path = Path(source_path)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == "ai-ressources":
        ai_resources = _ai_resources_root(project_root)
        return ai_resources.joinpath(*parts[1:])
    return project_root / path


def _ai_resources_root(project_root: Path) -> Path:
    configured = os.environ.get("AIRESOURCES")
    if configured:
        return Path(configured)
    manifest = project_root / ".conventions" / "manifest.yaml"
    try:
        raw = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return Path.home() / "projects" / "ai-ressources"
    if isinstance(raw, dict) and isinstance(raw.get("ai_resources_path"), str):
        return Path(raw["ai_resources_path"])
    return Path.home() / "projects" / "ai-ressources"


def _patterns(data: dict[str, Any]) -> list[AstPattern]:
    patterns = data.get("patterns")
    if not isinstance(patterns, list):
        raise AstCatalogError("rule patterns must be a list")
    parsed: list[AstPattern] = []
    for item in patterns:
        if not isinstance(item, dict):
            raise AstCatalogError("rule pattern must be a mapping")
        # Pattern entries have backend-specific payload fields, so cast after shape check.
        item_data = cast(dict[str, Any], item)
        parsed.append(
            AstPattern(kind=_string(item_data, "kind"), value=_string(item_data, "value"))
        )
    return parsed


def _severity(data: dict[str, Any]) -> Literal["warning", "error"]:
    severity = _string(data, "severity")
    if severity not in {"warning", "error"}:
        raise AstCatalogError("severity must be warning or error")
    return cast(Literal["warning", "error"], severity)


def _justification(data: dict[str, Any]) -> AstJustification:
    raw = data.get("justification")
    if raw is None:
        return AstJustification()
    if not isinstance(raw, dict):
        raise AstCatalogError("rule justification must be a mapping")
    # Justification policy is optional, but active entries must keep the supported v1 window.
    justification = cast(dict[str, Any], raw)
    accepted_window = justification.get("accepted_window", "adjacent_comment_block")
    if accepted_window != "adjacent_comment_block":
        raise AstCatalogError("justification.accepted_window must be adjacent_comment_block")
    return AstJustification(
        required=bool(justification.get("required", False)),
        accepted_window="adjacent_comment_block",
        rule_id_required=bool(justification.get("rule_id_required", True)),
    )


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise AstCatalogError(f"field invalid: {key}")
    return value

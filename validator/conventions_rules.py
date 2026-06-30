# @spec(AC-022)

# LiveSpec traceability anchors
# @spec FR-001: Rulebook schema, FR-002: Resolve sources, FR-003: Compile via provider, FR-004: Stale hashes — .specs/features/062-conventions-rulebook-semantic/spec.md#fr-001  # noqa: E501 - LiveSpec anchor paths must stay on one line.

"""Conventions rulebook schema, loader, and compiler."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from inspect import Parameter, signature
from pathlib import Path
from typing import Literal, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.
from pydantic import BaseModel, ConfigDict, Field, field_validator

from validator import llm_provider

RULEBOOK_RELATIVE_PATH = Path(".specs/conventions-rulebook.yaml")
# Matches the `.conventions/index.md` declaration that binds `$AIRESOURCES` to a root path.
_AIRESOURCES_RE = re.compile(r"`?\$AIRESOURCES`?\s*=\s*`([^`]+)`")
# Matches convention source lines and supports both the Unicode and ASCII arrows.
_SOURCE_LINE_RE = re.compile(r"^\s*(?:→|->)\s*(\$AIRESOURCES/[^\n]+)$")


class RulebookStaleError(RuntimeError):
    """Raised when an existing rulebook no longer matches convention sources."""


class ConventionsRulesBase(BaseModel):
    """Strict frozen base model for compiled rulebook YAML."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RulebookSource(ConventionsRulesBase):
    """One convention source included in a compiled rulebook."""

    path: str
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        """Validate SHA-256 shape."""
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("sha256 must be 64 lowercase hex chars")
        return value


class CompiledConventionRule(ConventionsRulesBase):
    """One semantic convention rule extracted from source conventions."""

    id: str
    domain: str
    description: str
    check: str
    source_excerpt: str
    blocking: bool = False
    applies_to: list[str] = Field(default_factory=list)
    source_paths: list[str] = Field(default_factory=list)


class UnenforceableConventionRule(ConventionsRulesBase):
    """Convention that is intentionally excluded from Engine C execution."""

    id: str
    domain: str
    reason: str
    source_path: str | None = None


class ConventionWaiver(ConventionsRulesBase):
    """Temporary semantic convention waiver."""

    rule_id: str
    reason: str
    expires: str
    path_glob: str | None = None

    @field_validator("expires")
    @classmethod
    def validate_expires(cls, value: str) -> str:
        """Validate ISO date waiver expiry."""
        try:
            datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("expires must use YYYY-MM-DD") from exc
        return value


class ConventionsRules(ConventionsRulesBase):
    """Root `.specs/conventions-rulebook.yaml` model."""

    schema_version: Literal[1]
    compiled_at: str
    sources: list[RulebookSource]
    rules: list[CompiledConventionRule]
    unenforceable: list[UnenforceableConventionRule] = Field(default_factory=list)
    waivers: list[ConventionWaiver] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> ConventionsRules:
        """Load a compiled rulebook from YAML."""
        return load_conventions_rules(path)


def rulebook_path(project_root: Path) -> Path:
    """Return the compiled conventions rulebook path."""
    return project_root / RULEBOOK_RELATIVE_PATH


def load_conventions_rules(path: Path) -> ConventionsRules:
    """Load and validate a compiled conventions rulebook.

    Args:
        path: Rulebook YAML file path.

    Returns:
        Validated rulebook model.

    Raises:
        FileNotFoundError: If the rulebook YAML does not exist.
        ValueError: If the YAML root is missing or malformed.
    """
    if path.is_dir():
        path = rulebook_path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid conventions rulebook yaml: {path}") from exc
    if not isinstance(raw, dict):
        raise ValueError("conventions rulebook root must be a mapping")
    return ConventionsRules.model_validate(raw)


def compile_conventions_rulebook(
    project_root: Path,
    *,
    force: bool = False,
    model: str | None = None,
) -> Path:
    """Compile `.conventions/index.md` into a self-contained rulebook.

    Args:
        project_root: Repository root containing `.conventions/index.md`.
        force: Overwrite stale existing rulebooks only when true.
        model: Optional model passed to the configured provider.

    Returns:
        Written rulebook path.

    Raises:
        FileNotFoundError: If `.conventions/index.md` or a referenced source is missing.
        RulebookStaleError: If an existing rulebook has stale source hashes and `force` is false.
        json.JSONDecodeError: If the provider response is not JSON.
    """
    root = project_root.resolve()
    sources = _resolve_convention_sources(root)
    output_path = rulebook_path(root)
    if output_path.exists() and not force:
        _raise_if_stale(output_path, sources)
        return output_path
    payload = _compile_payload(sources, model=model)
    rules = _payload_list(payload, "rules")
    unenforceable = _payload_list(payload, "unenforceable")
    waivers = _payload_list(payload, "waivers")
    rulebook = ConventionsRules(
        schema_version=1,
        compiled_at=datetime.now(UTC).isoformat(),
        sources=[
            RulebookSource(path=source.display_path, sha256=_sha256_text(source.content))
            for source in sources
        ],
        rules=[CompiledConventionRule.model_validate(rule) for rule in rules],
        unenforceable=[UnenforceableConventionRule.model_validate(rule) for rule in unenforceable],
        waivers=[ConventionWaiver.model_validate(waiver) for waiver in waivers],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_dump_yaml(rulebook.model_dump(exclude_none=True)), encoding="utf-8")
    return output_path


class _ResolvedSource(ConventionsRulesBase):
    display_path: str
    absolute_path: Path
    content: str


def _resolve_convention_sources(project_root: Path) -> list[_ResolvedSource]:
    index_path = project_root / ".conventions" / "index.md"
    if not index_path.is_file():
        raise FileNotFoundError(".conventions/index.md not found")
    index_text = index_path.read_text(encoding="utf-8")
    resources_root = _airesources_root(index_text)
    sources: list[_ResolvedSource] = []
    for raw_source in _source_entries(index_text):
        absolute = (resources_root / raw_source.removeprefix("$AIRESOURCES/")).resolve()
        try:
            absolute.relative_to(resources_root)
        except ValueError as exc:
            raise ValueError(f"conventions source escapes $AIRESOURCES: {raw_source}") from exc
        if not absolute.is_file():
            raise FileNotFoundError(f"conventions source not found: {raw_source}")
        sources.append(
            _ResolvedSource(
                display_path=raw_source,
                absolute_path=absolute,
                content=absolute.read_text(encoding="utf-8"),
            )
        )
    if not sources:
        raise ValueError(".conventions/index.md contains no source entries")
    return sources


def _airesources_root(index_text: str) -> Path:
    match = _AIRESOURCES_RE.search(index_text)
    if match:
        return Path(match.group(1)).expanduser().resolve()
    raise ValueError(".conventions/index.md must declare `$AIRESOURCES` root")


def _source_entries(index_text: str) -> list[str]:
    entries: list[str] = []
    for line in index_text.splitlines():
        match = _SOURCE_LINE_RE.match(line)
        if not match:
            continue
        head, *tail = [part.strip() for part in match.group(1).split(",")]
        base_dir = str(Path(head).parent)
        entries.append(head)
        entries.extend(f"{base_dir}/{item}" for item in tail if item)
    return entries


def _raise_if_stale(path: Path, sources: list[_ResolvedSource]) -> None:
    existing = load_conventions_rules(path)
    expected = {source.display_path: _sha256_text(source.content) for source in sources}
    recorded = {source.path: source.sha256 for source in existing.sources}
    if expected != recorded:
        raise RulebookStaleError("conventions rulebook source hashes are stale")


def _compile_payload(sources: list[_ResolvedSource], *, model: str | None) -> dict[str, object]:
    prompt = _compile_prompt(sources)
    raw = _call_provider(prompt, _RULEBOOK_SCHEMA, model=model)
    data: object = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("provider rulebook response must be an object")
    return cast(dict[str, object], data)


def _payload_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"provider rulebook response field must be a list: {key}")
    return value


def _compile_prompt(sources: list[_ResolvedSource]) -> str:
    blocks = "\n\n".join(
        f"## Source: {source.display_path}\n{source.content}" for source in sources
    )
    return (
        "Compile a self-contained LiveSpec conventions rulebook.\n"
        "Return only JSON matching the schema. Rules must include id, domain, "
        "description, check, source_excerpt, blocking, and source_paths. Temperature: 0.\n\n"
        f"{blocks}"
    )


def _call_provider(prompt: str, json_schema: dict[str, object], *, model: str | None) -> str:
    provider_call = cast(Callable[..., str], llm_provider.call_llm)
    parameters = signature(provider_call).parameters.values()
    supports_temperature = any(
        parameter.kind is Parameter.VAR_KEYWORD or parameter.name == "temperature"
        for parameter in parameters
    )
    if supports_temperature:
        return provider_call(prompt, json_schema=json_schema, model=model, temperature=0)
    return provider_call(prompt, json_schema=json_schema, model=model)


def _sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _dump_yaml(payload: object) -> str:
    return cast(str, yaml.safe_dump(payload, sort_keys=False, allow_unicode=False))


_RULEBOOK_SCHEMA: dict[str, object] = {
    "name": "conventions_rulebook",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "domain": {"type": "string"},
                        "description": {"type": "string"},
                        "check": {"type": "string"},
                        "source_excerpt": {"type": "string"},
                        "blocking": {"type": "boolean"},
                        "applies_to": {"type": "array", "items": {"type": "string"}},
                        "source_paths": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "id",
                        "domain",
                        "description",
                        "check",
                        "source_excerpt",
                        "blocking",
                        "applies_to",
                        "source_paths",
                    ],
                },
            },
            "unenforceable": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "domain": {"type": "string"},
                        "reason": {"type": "string"},
                        "source_path": {"type": "string"},
                    },
                    "required": ["id", "domain", "reason", "source_path"],
                },
            },
            "waivers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "rule_id": {"type": "string"},
                        "reason": {"type": "string"},
                        "expires": {"type": "string"},
                        "path_glob": {"type": "string"},
                    },
                    "required": ["rule_id", "reason", "expires", "path_glob"],
                },
            },
        },
        "required": ["rules", "unenforceable", "waivers"],
        "additionalProperties": False,
    },
}

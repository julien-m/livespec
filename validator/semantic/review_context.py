"""Complete, bounded and fingerprinted review inputs (078 FR-001, FR-002)."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from validator.semantic.review_identity import context_identity as _context_identity

POLICY_VERSION = "078.1"
SCHEMA_VERSION = "1"
PROMPT_VERSION = "2"
DEFAULT_MAX_CHARS = 60000  # Conservative characters, deliberately not advertised as tokens.
_REQUIREMENT = re.compile(r"\b(?:FR|AC|SC)-\d+\b")


class ReviewSection(BaseModel):
    """Exact source span, including its original lines and UTF-8 byte offsets."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    section_id: str
    source: str
    role: str
    text: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int


class ReviewRequirement(BaseModel):
    """One qualified obligation retaining all repeated declaration spans."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    requirement_id: str
    section_ids: tuple[str, ...]


class ReviewBatch(BaseModel):
    """A bounded submission with complete source sections and shared invariants."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    batch_id: str
    section_ids: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    prompt: str


class PreparedReview(BaseModel):
    """Immutable preparation shared by native and provider transports."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    feature: str
    kind: Literal["spec", "plan"]
    reviewer_model: str
    context_hash: str
    source_hashes: dict[str, str]
    dependencies: dict[str, str] = Field(default_factory=dict)
    sections: tuple[ReviewSection, ...]
    requirements: tuple[ReviewRequirement, ...]
    requirement_scope: tuple[str, ...] | None = None
    batches: tuple[ReviewBatch, ...]
    errors: tuple[str, ...]
    max_chars: int
    policy_version: str = POLICY_VERSION
    schema_version: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION

    @property
    def complete(self) -> bool:
        """Whether every source can be submitted within the declared budget."""
        return not self.errors and bool(self.batches)

    @property
    def cacheable(self) -> bool:
        """Unresolved provider defaults cannot establish exact model identity."""
        return self.complete and self.reviewer_model not in ("", "default", "unknown")


def is_lifecycle_source(source: str, role: str, feature: str) -> bool:
    """Only selected canonical spec/plan metadata can change without invalidation."""
    return role in ("spec", "plan") and (
        source == role or source.endswith(f".specs/features/{feature}/{role}.md")
    )


def content_hash(text: str) -> str:
    """Hash exact UTF-8 input bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sections(source: str, text: str, role: str) -> list[ReviewSection]:
    lines = text.splitlines(keepends=True)
    starts = [0]
    fenced = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if index and not fenced and re.match(r"^#{1,6}\s", line):
            starts.append(index)
    result = []
    for start, end in zip(starts, [*starts[1:], len(lines)], strict=True):
        chunk = "".join(lines[start:end])
        if not chunk:
            continue
        result.append(
            ReviewSection(
                section_id=f"{source}:L{start + 1}-L{end}",
                source=source,
                role=role,
                text=chunk,
                start_line=start + 1,
                end_line=end,
                start_byte=len("".join(lines[:start]).encode()),
                end_byte=len("".join(lines[:end]).encode()),
            )
        )
    return result


def _inventory(
    sections: list[ReviewSection], feature: str, source_features: dict[str, str]
) -> tuple[ReviewRequirement, ...]:
    spans: dict[str, list[str]] = {}
    for section in sections:
        if section.role not in ("spec", "reference"):
            continue
        owner = source_features.get(section.source, feature)
        for local_id in dict.fromkeys(_REQUIREMENT.findall(section.text)):
            spans.setdefault(f"{owner}:{local_id}", []).append(section.section_id)
    return tuple(
        ReviewRequirement(requirement_id=key, section_ids=tuple(value))
        for key, value in sorted(spans.items())
    )


def _duplicate_errors(
    sections: list[ReviewSection], feature: str, owners: dict[str, str]
) -> list[str]:
    declarations: dict[str, str] = {}
    errors = []
    for section in sections:
        if section.role not in ("spec", "reference"):
            continue
        heading = re.match(r"^#{1,6}\s+((?:FR|AC|SC)-\d+)\s*\n", section.text)
        if heading is None:
            continue
        key = f"{owners.get(section.source, feature)}:{heading[1]}"
        body = section.text[heading.end() :].strip()
        if key in declarations and declarations[key] != body:
            errors.append(f"conflicting_duplicate_definition:{key}")
        declarations[key] = body
    return errors


def _scope_requirements(
    inventory: tuple[ReviewRequirement, ...], scope: tuple[str, ...]
) -> tuple[tuple[ReviewRequirement, ...], list[str]]:
    errors = []
    available = {item.requirement_id for item in inventory}
    if not scope:
        errors.append("empty_requirement_scope")
    if len(scope) != len(set(scope)):
        errors.append("duplicate_requirement_scope")
    errors.extend(f"unknown_scoped_requirement:{key}" for key in scope if key not in available)
    return tuple(item for item in inventory if item.requirement_id in scope), errors


def _scoped_batches(
    kind: Literal["spec", "plan"],
    sections: list[ReviewSection],
    requirements: tuple[ReviewRequirement, ...],
    requirement_scope: tuple[str, ...] | None,
    max_chars: int,
) -> tuple[tuple[ReviewRequirement, ...], tuple[ReviewBatch, ...], list[str]]:
    """Build complete-context batches with optional explicitly limited obligations."""
    from validator.semantic.review_batches import build_batches

    scope_errors: list[str] = []
    scope_prefix = ""
    if requirement_scope is not None:
        requirements, scope_errors = _scope_requirements(requirements, requirement_scope)
        scope_prefix = (
            "Only the listed requirement IDs are conclusion obligations. All other normative "
            "sections remain context; do not invent missing coverage for deliberately unselected "
            "requirements. Report actual blocking issues affecting the selected scope.\n"
        )
    batches, errors = build_batches(kind, sections, requirements, max_chars - len(scope_prefix))
    if scope_prefix:
        batches = tuple(
            batch.model_copy(update={"prompt": scope_prefix + batch.prompt}) for batch in batches
        )
    errors.extend(scope_errors)
    return requirements, batches, errors


def _prepare_sections(
    feature: str,
    kind: Literal["spec", "plan"],
    sources: dict[str, str],
    roles: dict[str, str],
    owners: dict[str, str],
    requirement_scope: tuple[str, ...] | None,
    max_chars: int,
    unresolved_references: tuple[str, ...],
) -> tuple[list[ReviewSection], tuple[ReviewRequirement, ...], tuple[ReviewBatch, ...], list[str]]:
    """Retain complete source inventory and all preparation diagnostics."""
    sections = [
        section
        for name, text in sorted(sources.items())
        for section in _sections(name, text, roles.get(name, name))
    ]
    requirements = _inventory(sections, feature, owners)
    requirements, batches, errors = _scoped_batches(
        kind, sections, requirements, requirement_scope, max_chars
    )
    errors.extend(_duplicate_errors(sections, feature, owners))
    errors.extend(f"unresolved_reference:{ref}" for ref in unresolved_references)
    if not any(s.role == "spec" for s in sections):
        errors.append("missing_spec")
    if kind == "plan" and not any(s.role == "plan" for s in sections):
        errors.append("missing_plan")
    return sections, requirements, batches, errors


def prepare_review_context(
    feature: str,
    sources: dict[str, str],
    *,
    kind: Literal["spec", "plan"] = "plan",
    model: str = "",
    source_roles: dict[str, str] | None = None,
    source_features: dict[str, str] | None = None,
    dependencies: dict[str, str] | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    unresolved_references: tuple[str, ...] = (),
    requirement_scope: tuple[str, ...] | None = None,
) -> PreparedReview:
    """Prepare supplied bytes only; callers must resolve filesystem dependencies explicitly."""
    roles = source_roles or {}
    owners = source_features or {}
    sections, requirements, batches, errors = _prepare_sections(
        feature, kind, sources, roles, owners, requirement_scope, max_chars, unresolved_references
    )
    hashes = {name: content_hash(text) for name, text in sorted(sources.items())}
    identity = _context_identity(
        feature,
        kind,
        model,
        sources,
        roles,
        owners,
        dependencies,
        max_chars,
        unresolved_references,
        requirement_scope,
    )
    return PreparedReview(
        feature=feature,
        kind=kind,
        reviewer_model=model,
        context_hash=identity,
        source_hashes=hashes,
        dependencies=dependencies or {},
        sections=tuple(sections),
        requirements=requirements,
        requirement_scope=requirement_scope,
        batches=batches,
        errors=tuple(errors),
        max_chars=max_chars,
    )

"""Declared acceptance proof types, independent of incidental AC references."""

# @spec(FR-009)
# @spec(FR-016)

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AcceptanceRequirement(BaseModel):
    """One canonical AC with explicit documentary inputs when applicable."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    requirement_id: str
    evidence_kind: Literal["execution", "review"] = "execution"
    review_inputs: tuple[str, ...] = ()


def acceptance_inventory(
    project_root: Path,
    feature: str,
    *,
    spec_text: str | None = None,
) -> tuple[AcceptanceRequirement, ...]:
    """Read headings and acceptance-table declarations; ignore references and fenced examples."""
    root = project_root.resolve()
    spec = root / ".specs/features" / feature / "spec.md"
    spec.resolve().relative_to(root / ".specs/features")
    if spec_text is None and not spec.is_file():
        return ()
    declarations = _declarations(
        spec_text if spec_text is not None else spec.read_bytes().decode("utf-8")
    )
    return tuple(
        _requirement(root, spec, feature, key, values)
        for key, values in sorted(declarations.items())
    )


def execution_acceptance_ids(
    project_root: Path,
    feature: str,
    *,
    spec_text: str | None = None,
) -> tuple[str, ...]:
    """Return only obligations whose declared evidence is an executed assertion."""
    return tuple(
        item.requirement_id
        for item in acceptance_inventory(project_root, feature, spec_text=spec_text)
        if item.evidence_kind == "execution"
    )


_AC_HEADING = re.compile(r"^(AC-\d+)(?:\s|:|$)")
_ACCEPTANCE_TITLES = {"acceptance criteria", "critères d'acceptation"}


def _visible_lines(text: str) -> list[str]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    result: list[str] = []
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = ""
            continue
        if marker:
            fence = marker[1]
            continue
        result.append(line)
    return result


def _scope_allows_declaration(stack: list[tuple[int, str]], explicit: bool) -> bool:
    if any(title.casefold() in {"references", "examples"} for _, title in stack):
        return False
    if any(title.casefold() in _ACCEPTANCE_TITLES for _, title in stack):
        return True
    return not explicit and (
        not stack
        or (
            len(stack) == 1
            and stack[0][0] == 1
            and stack[0][1].casefold() not in {"references", "examples"}
        )
    )


def _declarations(text: str) -> dict[str, list[str]]:
    lines = _visible_lines(text)
    explicit = any(
        re.sub(r"^#{1,6}\s+", "", line).casefold() in _ACCEPTANCE_TITLES for line in lines
    )
    declarations: dict[str, list[str]] = {}
    stack: list[tuple[int, str]] = []
    current: str | None = None
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading:
            level, title = len(heading[1]), heading[2].strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            match = _AC_HEADING.match(title)
            allowed = _scope_allows_declaration(stack, explicit)
            current = match[1] if match and allowed else None
            if current:
                declarations.setdefault(current, [])
            stack.append((level, title))
        allowed = _scope_allows_declaration(stack, explicit)
        table = re.match(r"^\|\s*(AC-\d+)\s*\|", line) if allowed else None
        standalone = (
            re.match(r"^(AC-\d+)\s*:", line)
            if allowed and not any(_AC_HEADING.match(title) for _, title in stack)
            else None
        )
        if table or standalone:
            match = table or standalone
            assert match is not None
            declarations.setdefault(match[1], [])
            if standalone:
                current = standalone[1]
        line = re.sub(r"^ {1,3}(?=\S)", "", line)
        if current and re.match(r"^\*\*(?:Evidence|Review inputs)\b", line, re.IGNORECASE):
            if not line.startswith(("**Evidence:**", "**Review inputs:**")):
                raise ValueError(f"malformed_acceptance_metadata:{current}")
            declarations[current].append(line)
    return declarations


def _requirement(
    root: Path, spec: Path, feature: str, key: str, metadata: list[str]
) -> AcceptanceRequirement:
    kinds = {
        line.removeprefix("**Evidence:**").strip()
        for line in metadata
        if line.startswith("**Evidence:**")
    }
    if kinds - {"execution", "review"} or len(kinds) > 1:
        raise ValueError(f"invalid_or_conflicting_acceptance_evidence:{key}")
    kind = next(iter(kinds), "execution")
    inputs: set[str] = set()
    for line in metadata:
        if not line.startswith("**Review inputs:**"):
            continue
        for target in re.findall(r"\[[^]]*\]\(<?([^)>]+)>?\)", line):
            path = (spec.parent / target).resolve()
            inputs.add(path.relative_to(root).as_posix())
    if (kind == "review") != bool(inputs):
        raise ValueError(f"acceptance_review_inputs_required_only_for_review:{key}")
    return AcceptanceRequirement(
        requirement_id=f"{feature}:{key}",
        evidence_kind="review" if kind == "review" else "execution",
        review_inputs=tuple(sorted(inputs)),
    )

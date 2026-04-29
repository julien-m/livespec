"""Grammar validator for brainstorm flow files.

Checks frontmatter required fields, required H2 sections, and ID prefix
conventions on `specs/flows/*.md`. Also resolves mockup references against
the on-disk `mockups/` directory. All violations are collected in a single
pass — no early exit — so the full list can be reported atomically before
any write (FR-003 / AC-004).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]
from pydantic import ValidationError

from .schemas import FlowFrontmatter, Violation

REQUIRED_FRONTMATTER_FIELDS = (
    "flow",
    "title",
    "status",
    "priority",
    "mockups",
    "surfaces",
    "source",
    "generated_at",
)

REQUIRED_SECTIONS = (
    "User Scenarios & Testing",
    "Acceptance Criteria",
    "Functional Requirements",
    "Key Entities",
    "Edge Cases",
    "Success Criteria",
)

ALLOWED_PRIORITIES = ("P1", "P2", "P3", None)

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_ID_RE = re.compile(r"\b(AC|FR|SC)-(\d{3})\b")


@dataclass
class FlowValidationResult:
    """Outcome of validating a single flow file."""

    path: Path
    frontmatter: FlowFrontmatter | None = None
    body: str = ""
    violations: list[Violation] = field(default_factory=list[Violation])

    @property
    def ok(self) -> bool:
        return not self.violations and self.frontmatter is not None


@dataclass
class ValidationReport:
    """Aggregate validation report across all flows + mockup resolution."""

    flows: list[FlowValidationResult] = field(default_factory=list[FlowValidationResult])
    mockup_violations: list[Violation] = field(default_factory=list[Violation])

    @property
    def all_violations(self) -> list[Violation]:
        out: list[Violation] = []
        for f in self.flows:
            out.extend(f.violations)
        out.extend(self.mockup_violations)
        return out

    @property
    def ok(self) -> bool:
        return not self.all_violations


def _check_frontmatter(
    raw: dict[str, Any], rel: str
) -> tuple[FlowFrontmatter | None, list[Violation]]:
    """Verify required fields are present; build a typed FlowFrontmatter."""
    violations: list[Violation] = []
    for field_name in REQUIRED_FRONTMATTER_FIELDS:
        if field_name not in raw:
            violations.append(
                Violation(
                    file=rel,
                    rule_id="FRONTMATTER_MISSING_FIELD",
                    message=f"missing frontmatter field {field_name!r}",
                )
            )
    priority = raw.get("priority")
    if priority is not None and priority not in ALLOWED_PRIORITIES:
        violations.append(
            Violation(
                file=rel,
                rule_id="FRONTMATTER_BAD_PRIORITY",
                message=f"priority must be P1/P2/P3 or omitted, got {priority!r}",
            )
        )
    surfaces = raw.get("surfaces")
    if isinstance(surfaces, list) and surfaces == []:
        violations.append(
            Violation(
                file=rel,
                rule_id="FRONTMATTER_EMPTY_SURFACES",
                message="surfaces array must not be empty",
            )
        )
    if violations:
        return None, violations
    try:
        fm = FlowFrontmatter.model_validate(
            {k: raw.get(k) for k in REQUIRED_FRONTMATTER_FIELDS}
        )
    except ValidationError as exc:
        return None, [
            Violation(
                file=rel,
                rule_id="FRONTMATTER_INVALID",
                message=f"frontmatter shape error: {exc}",
            )
        ]
    return fm, []


def _check_sections(body: str, rel: str) -> list[Violation]:
    """Verify all required H2 sections are present."""
    headings = {m.group(1).strip() for m in _H2_RE.finditer(body)}
    violations: list[Violation] = []
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            violations.append(
                Violation(
                    file=rel,
                    rule_id="SECTION_MISSING",
                    message=f"missing section ## {section}",
                )
            )
    return violations


def _check_ids(body: str, rel: str) -> list[Violation]:
    """Verify at least one AC/FR/SC ID is declared somewhere in the body."""
    matches = _ID_RE.findall(body)
    if not matches:
        return [
            Violation(
                file=rel,
                rule_id="IDS_MISSING",
                message="no AC-/FR-/SC- IDs found in body",
            )
        ]
    return []


# @spec FR-002: Grammar gate — .specs/features/012-brainstorm-ingestion/spec.md#fr-002
def validate_flow(path: Path) -> FlowValidationResult:
    """Validate a single flow.md file (frontmatter + sections + IDs)."""
    rel = path.name
    if not path.exists():
        return FlowValidationResult(
            path=path,
            violations=[
                Violation(file=rel, rule_id="FILE_MISSING", message=f"flow not found: {path}")
            ],
        )
    raw = frontmatter.load(str(path))
    fm, fm_violations = _check_frontmatter(dict(raw.metadata), rel)
    body = raw.content
    section_violations = _check_sections(body, rel)
    id_violations = _check_ids(body, rel)
    return FlowValidationResult(
        path=path,
        frontmatter=fm,
        body=body,
        violations=fm_violations + section_violations + id_violations,
    )


# @spec FR-003: Mockup resolution check — .specs/features/012-brainstorm-ingestion/spec.md#fr-003
def validate_mockup_refs(
    flow_results: list[FlowValidationResult],
    mockups_dir: Path,
) -> list[Violation]:
    """For every flow's referenced mockup, assert the PNG exists."""
    violations: list[Violation] = []
    for fr in flow_results:
        if fr.frontmatter is None:
            continue
        for raw_ref in fr.frontmatter.mockups:
            ref = raw_ref if raw_ref.endswith(".png") else f"{raw_ref}.png"
            target = mockups_dir / ref
            if not target.exists():
                violations.append(
                    Violation(
                        file=fr.path.name,
                        rule_id="MOCKUP_MISSING",
                        message=f"missing mockup file: {ref}",
                    )
                )
    return violations


def validate_all(cwd: Path) -> ValidationReport:
    """Validate every `specs/flows/*.md` and resolve mockup refs.

    Collects all violations across files in a single pass.
    """
    flows_dir = cwd / "specs" / "flows"
    mockups_dir = cwd / "mockups"
    report = ValidationReport()
    if not flows_dir.exists():
        return report
    flow_paths = sorted(p for p in flows_dir.glob("*.md") if p.name != "_index.md")
    for path in flow_paths:
        report.flows.append(validate_flow(path))
    if mockups_dir.exists():
        report.mockup_violations = validate_mockup_refs(report.flows, mockups_dir)
    else:
        # If any flow references a mockup, missing dir is a violation.
        for fr in report.flows:
            if fr.frontmatter and fr.frontmatter.mockups:
                report.mockup_violations.append(
                    Violation(
                        file=fr.path.name,
                        rule_id="MOCKUPS_DIR_MISSING",
                        message="mockups/ directory not found but flow references mockups",
                    )
                )
                break
    return report

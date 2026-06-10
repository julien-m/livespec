# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-010)

"""README registry target: row update, Recent Activity regeneration, rebuild.

Private helper module for :mod:`validator.finalize` (300-line constitution
cap). Consumes the *new* global changelog content so the regenerated Recent
Activity reflects the entry inserted by the same apply run.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from .finalize_registry import marker_pattern

if TYPE_CHECKING:  # Circular: finalize defines ApplyRequest and imports this module
    from .finalize import ApplyRequest

_FEATURES_START = "<!-- readme:features:start -->"
_FEATURES_END = "<!-- readme:features:end -->"
_ACTIVITY_START = "<!-- readme:activity:start -->"
_ACTIVITY_END = "<!-- readme:activity:end -->"
_DECISIONS_START = "<!-- readme:decisions:start -->"
_DECISIONS_END = "<!-- readme:decisions:end -->"

RECENT_ACTIVITY_CAP = 10
"""README Recent Activity is capped at 10 entries (spec-system.md)."""

# Matches one global changelog entry: "## YYYY-MM-DD — <description>".
_CHANGELOG_ENTRY_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — (.+)$", re.MULTILINE)
_LAST_UPDATED_RE = re.compile(r"^> Last updated: \d{4}-\d{2}-\d{2}$", re.MULTILINE)


def build_readme(
    path: Path,
    request: ApplyRequest,
    today: date,
    marker: str,
    global_changelog_content: str,
    specs_root: Path,
) -> str:
    """Return the new README content for one apply run.

    Updates the feature row (status + updated date), regenerates Recent
    Activity from the new global changelog, refreshes ``Last updated``, and
    stamps the idempotence marker. Rebuilds the whole file from artifacts
    when it is missing (FR-010 / AC-012).
    """
    if path.is_file():
        content = path.read_text(encoding="utf-8")
    else:
        content = _rebuild_readme_skeleton(specs_root, today)
    content = _update_feature_row(content, request, today, specs_root)
    content = _regenerate_activity(content, global_changelog_content)
    content = _LAST_UPDATED_RE.sub(f"> Last updated: {today.isoformat()}", content)
    if not marker_pattern(request.command, request.hash8()).search(content):
        content = f"{content.rstrip()}\n\n{marker}\n"
    return content


def _feature_number(feature_slug: str) -> str:
    # Slug shape is NNN-name or NNN.M-name; the number is the row key.
    return feature_slug.split("-", 1)[0]


def _update_feature_row(
    content: str,
    request: ApplyRequest,
    today: date,
    specs_root: Path,
) -> str:
    number = _feature_number(request.feature_slug)
    lines = content.splitlines()
    row_prefix = f"| {number} |"
    for index, line in enumerate(lines):
        if line.startswith(row_prefix):
            lines[index] = _render_row_update(line, request.status, today)
            return "\n".join(lines) + "\n"
    # Row absent (e.g. rebuilt README raced a manual edit): insert a fresh row
    # before the features end marker so the registry never loses the feature.
    new_row = _render_new_row(request, today, specs_root)
    return _insert_before(content, _FEATURES_END, new_row)


def _render_row_update(line: str, status: str | None, today: date) -> str:
    cells = line.split("|")
    # Row shape: | # | Feature | Status | Created | Updated | Spec | → 8 cells
    # after split (leading/trailing empties included).
    if len(cells) >= 7:
        if status is not None:
            cells[3] = f" {status} "
        cells[5] = f" {today.isoformat()} "
    return "|".join(cells)


def _render_new_row(request: ApplyRequest, today: date, specs_root: Path) -> str:
    number = _feature_number(request.feature_slug)
    spec_path = specs_root / "features" / request.feature_slug / "spec.md"
    title = _spec_title(spec_path, request.feature_slug)
    created = _frontmatter_value(spec_path, "created") or today.isoformat()
    status = request.status or _frontmatter_value(spec_path, "status") or "Draft"
    return (
        f"| {number} | {title} | {status} | {created} | {today.isoformat()} | "
        f"[spec](features/{request.feature_slug}/spec.md) |"
    )


def _regenerate_activity(content: str, global_changelog_content: str) -> str:
    rows = ["| Date | Type | Description |", "|---|---|---|"]
    entries = _CHANGELOG_ENTRY_RE.findall(global_changelog_content)[:RECENT_ACTIVITY_CAP]
    for entry_date, description in entries:
        rows.append(f"| {entry_date} | {_entry_type(description)} | {description} |")
    return _replace_between(content, _ACTIVITY_START, _ACTIVITY_END, "\n".join(rows))


def _entry_type(description: str) -> str:
    # Deterministic Type column mapping derived from the changelog summary
    # wording conventions (spec-system.md changelog format).
    if "Spec created" in description or description.startswith("Spec"):
        return "Spec"
    if "Plan created" in description:
        return "Plan"
    if "Fix" in description or "Bugfix" in description:
        return "Bugfix"
    if "Check:" in description:
        return "Check"
    return "Feature"


def _replace_between(content: str, start: str, end: str, body: str) -> str:
    start_index = content.find(start)
    end_index = content.find(end)
    if start_index == -1 or end_index == -1 or end_index < start_index:
        # Markers absent (hand-edited README): append a fresh marked section
        # instead of corrupting unrelated content.
        return f"{content.rstrip()}\n\n{start}\n{body}\n{end}\n"
    head = content[: start_index + len(start)]
    tail = content[end_index:]
    return f"{head}\n{body}\n{tail}"


def _insert_before(content: str, anchor: str, line: str) -> str:
    index = content.find(anchor)
    if index == -1:
        return f"{content.rstrip()}\n{line}\n"
    return content[:index] + line + "\n" + content[index:]


def _rebuild_readme_skeleton(specs_root: Path, today: date) -> str:
    """Rebuild README.md from existing artifacts (spec-system README Recovery).

    @spec FR-010: rebuild missing README from artifacts
    — .specs/features/058-deterministic-finalization/spec.md#fr-010
    """
    feature_rows = [
        "| # | Feature | Status | Created | Updated | Spec |",
        "|---|---|---|---|---|---|",
    ]
    features_dir = specs_root / "features"
    if features_dir.is_dir():
        for spec_path in sorted(features_dir.glob("*/spec.md")):
            slug = spec_path.parent.name
            number = _feature_number(slug)
            title = _spec_title(spec_path, slug)
            status = _frontmatter_value(spec_path, "status") or "Draft"
            created = _frontmatter_value(spec_path, "created") or today.isoformat()
            updated = _frontmatter_value(spec_path, "updated") or created
            feature_rows.append(
                f"| {number} | {title} | {status} | {created} | {updated} | "
                f"[spec](features/{slug}/spec.md) |"
            )
    decision_rows = ["| ADR | Decision | Date | Status |", "|---|---|---|---|"]
    decisions_dir = specs_root / "stacks" / "decisions"
    if decisions_dir.is_dir():
        for adr_path in sorted(decisions_dir.glob("ADR-*.md")):
            adr_id = adr_path.stem.split("-", 2)
            adr_name = adr_id[2].replace("-", " ") if len(adr_id) > 2 else adr_path.stem
            decision_rows.append(
                f"| {'-'.join(adr_id[:2])} | {adr_name} | {today.isoformat()} | Active |"
            )
    return "\n".join(
        [
            "# .specs — Spec Registry",
            "",
            "> Rebuilt automatically by `livespec finalize apply` (README Recovery).",
            ">",
            f"> Last updated: {today.isoformat()}",
            "",
            "## Features",
            "",
            _FEATURES_START,
            "\n".join(feature_rows),
            _FEATURES_END,
            "",
            "## Architecture Decisions",
            "",
            _DECISIONS_START,
            "\n".join(decision_rows),
            _DECISIONS_END,
            "",
            "## Recent Activity",
            "",
            _ACTIVITY_START,
            "| Date | Type | Description |",
            "|---|---|---|",
            _ACTIVITY_END,
            "",
        ]
    )


def _spec_title(spec_path: Path, fallback_slug: str) -> str:
    title = _frontmatter_value(spec_path, "title")
    if title:
        return title
    # Fallback: derive a human title from the slug (no spec frontmatter).
    return fallback_slug.split("-", 1)[-1].replace("-", " ").title()


def _frontmatter_value(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    match = re.search(rf'^{re.escape(key)}:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else None

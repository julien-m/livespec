# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-010)

"""Registry update builders for ``livespec finalize apply``.

Private helper module for :mod:`validator.finalize` (300-line constitution
cap — see plan.md Constitution Check deviation note). Builders render the
new content for the changelog/spec-status registry targets; README content
lives in :mod:`validator.finalize_readme`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .finalize_receipt import MARKER_TEMPLATE, FinalizeError

if TYPE_CHECKING:  # Circular: finalize defines ApplyRequest and imports this module
    from .finalize import ApplyRequest

RegistryTarget = Literal["feature_changelog", "global_changelog", "readme", "spec_status"]

# Fixed apply order (FR-001): changelogs first so the README Recent Activity
# regeneration reads the freshly inserted global summary from disk.
APPLY_TARGET_ORDER: tuple[RegistryTarget, ...] = (
    "feature_changelog",
    "global_changelog",
    "readme",
    "spec_status",
)

# Matches one global changelog entry heading: "## YYYY-MM-DD — <text>".
_ENTRY_HEADING_RE = re.compile(r"^## (\d{4})-\d{2}-\d{2} — ", re.MULTILINE)
_ARCHIVE_LINK_PREFIX = "> Archive: "


@dataclass(frozen=True)
class RegistryUpdate:
    """One declarative registry write applied under the lock."""

    target: RegistryTarget
    path: Path
    content: str


def render_marker(command: str, today: date, hash8: str) -> str:
    """Render the idempotence marker for a command/date/hash8 triple."""
    return MARKER_TEMPLATE.format(command=command, date=today.isoformat(), hash8=hash8)


def marker_pattern(command: str, hash8: str) -> re.Pattern[str]:
    """Return the identity pattern: ``<cmd>`` + ``<hash8>`` (date is a wildcard).

    @spec FR-002: marker identity is cmd+hash8, date informational
    — .specs/features/058-deterministic-finalization/spec.md#fr-002
    """
    return re.compile(rf"<!-- finalize:{re.escape(command)}:[0-9-]*:{re.escape(hash8)} -->")


def target_path(project_root: Path, target: RegistryTarget, feature_slug: str) -> Path:
    """Return the on-disk path of one registry target."""
    specs = project_root / ".specs"
    feature_dir = specs / "features" / feature_slug
    paths: dict[RegistryTarget, Path] = {
        "feature_changelog": feature_dir / "changelog.md",
        "global_changelog": specs / "changelog.md",
        "readme": specs / "README.md",
        "spec_status": feature_dir / "spec.md",
    }
    return paths[target]


def is_target_marked(path: Path, command: str, hash8: str) -> bool:
    """Return True when ``path`` already carries the cmd+hash8 marker."""
    if not path.is_file():
        return False
    return bool(marker_pattern(command, hash8).search(path.read_text(encoding="utf-8")))


def build_feature_changelog(path: Path, request: ApplyRequest, today: date, marker: str) -> str:
    """Append the date-rendered entry + marker to the feature changelog."""
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = f"# Changelog - {request.feature_slug}\n"
    # The entry body is date-free (FR-002); the first body line joins the
    # dated heading, remaining lines follow verbatim.
    lines = request.entry_body.strip().splitlines()
    heading = f"### {today.isoformat()} — {lines[0] if lines else ''}"
    rest = "\n".join(lines[1:]).strip()
    entry = heading + (f"\n\n{rest}" if rest else "")
    return f"{existing.rstrip()}\n\n{entry}\n\n{marker}\n"


def build_global_changelog(
    path: Path,
    request: ApplyRequest,
    today: date,
    marker: str,
) -> tuple[str, dict[int, str]]:
    """Insert the summary line and rotate previous-year entries.

    Returns:
        The new changelog content and a ``{year: archived_text}`` map for
        entries rotated to ``.specs/archive/changelog-YYYY.md`` (FR-010).
    """
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Changelog\n\n---\n"
    previously_archived_years = {
        int(year) for year in re.findall(r"\[(\d{4})\]\(archive/changelog-\d{4}\.md\)", existing)
    }
    kept, archived = _split_previous_years(existing, today.year)
    new_entry = f"## {today.isoformat()} — {request.global_summary.strip()}\n{marker}\n"
    # Entries are newest-first: insert before the first existing entry heading.
    match = _ENTRY_HEADING_RE.search(kept)
    if match:
        insert_at = match.start()
        content = kept[:insert_at] + new_entry + "\n" + kept[insert_at:]
    else:
        content = kept.rstrip() + "\n\n" + new_entry
    # Re-render the archive link section with both the years rotated by this
    # run and the years archived by earlier runs (the split strips the line).
    all_archive_years = previously_archived_years | set(archived)
    if all_archive_years:
        content = _append_archive_links(content, sorted(all_archive_years))
    return content, archived


def _split_previous_years(content: str, current_year: int) -> tuple[str, dict[int, str]]:
    """Separate previous-year entry blocks from the current-year changelog.

    Strategy (diff-style split): each block spans from its ``## YYYY-MM-DD``
    heading to the next heading (or EOF). Blocks whose year predates
    ``current_year`` are grouped per year for archiving; everything else is
    kept in order.
    """
    matches = list(_ENTRY_HEADING_RE.finditer(content))
    if not matches:
        return content, {}
    kept_parts = [content[: matches[0].start()]]
    archived: dict[int, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[match.start() : end]
        year = int(match.group(1))
        if year < current_year:
            archived[year] = archived.get(year, "") + block.rstrip() + "\n\n"
        else:
            kept_parts.append(block)
    kept = "".join(kept_parts)
    # Strip a pre-existing archive link section; it is re-rendered when needed.
    kept = "\n".join(
        line for line in kept.splitlines() if not line.startswith(_ARCHIVE_LINK_PREFIX)
    )
    return kept, archived


def _append_archive_links(content: str, years: list[int]) -> str:
    links = " | ".join(f"[{year}](archive/changelog-{year}.md)" for year in years)
    return f"{content.rstrip()}\n\n{_ARCHIVE_LINK_PREFIX}{links}\n"


def build_spec_status(path: Path, request: ApplyRequest, marker: str, today: date) -> str:
    """Update the spec status in frontmatter + header, kept in sync.

    Raises:
        FinalizeError: ``state_invalid`` naming the file when either status
            anchor is absent or non-standard (Edge Case 10) — apply never
            guesses an insertion point.
    """
    if not path.is_file():
        raise FinalizeError(f"spec_status target missing: {path}", subtype="state_invalid")
    content = path.read_text(encoding="utf-8")
    status = request.status or ""
    frontmatter_re = re.compile(r"^status:\s*\S.*$", re.MULTILINE)
    header_re = re.compile(r"^- \*\*Status:\*\* \S.*$", re.MULTILINE)
    if not frontmatter_re.search(content) or not header_re.search(content):
        raise FinalizeError(
            f"spec status anchors missing or non-standard in {path}",
            subtype="state_invalid",
        )
    content = frontmatter_re.sub(f"status: {status}", content, count=1)
    content = header_re.sub(f"- **Status:** {status}", content, count=1)
    updated_re = re.compile(r"^updated:\s*\S.*$", re.MULTILINE)
    if updated_re.search(content):
        content = updated_re.sub(f"updated: {today.isoformat()}", content, count=1)
    if not marker_pattern(request.command, request.hash8()).search(content):
        content = f"{content.rstrip()}\n\n{marker}\n"
    return content

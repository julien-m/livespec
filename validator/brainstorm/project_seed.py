"""Seed `.specs/project.md` and `.specs/stacks/_default.md` from `project-profile.md`.

When `project-profile.md` is present, extract free-form sections and emit
two seeded files. When absent, emit minimal scaffolds with
`[NEEDS INTERACTIVE FILL]` markers — the slash command (`commands/init.md`)
prompts the user to complete them.
"""

from __future__ import annotations

import re
from pathlib import Path

_SECTION_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.MULTILINE)


def _extract_section(profile_md: str, names: tuple[str, ...]) -> str | None:
    """Find the first section whose heading matches any of `names`."""
    matches = list(_SECTION_RE.finditer(profile_md))
    for i, m in enumerate(matches):
        title = m.group(1).strip().lower()
        if any(n.lower() in title for n in names):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(profile_md)
            return profile_md[start:end].strip()
    return None


# @spec FR-011: project.md seed — .specs/features/012-brainstorm-ingestion/spec.md#fr-011
def seed_project_md(profile_path: Path | None) -> str:
    """Build `.specs/project.md` body from `project-profile.md`.

    Absent profile → minimal scaffold with `[NEEDS INTERACTIVE FILL]` markers
    that the slash command will resolve via interactive prompt (FR-011 / AC-012).
    """
    if profile_path is None or not profile_path.exists():
        return (
            "# Project\n\n"
            "## Name\n\n[NEEDS INTERACTIVE FILL]\n\n"
            "## Vision\n\n[NEEDS INTERACTIVE FILL]\n\n"
            "## Audience\n\n[NEEDS INTERACTIVE FILL]\n\n"
            "## Constraints\n\n[NEEDS INTERACTIVE FILL]\n"
        )

    md = profile_path.read_text(encoding="utf-8")
    name = _extract_section(md, ("name",)) or "[NEEDS INTERACTIVE FILL]"
    vision = _extract_section(md, ("vision",)) or "[NEEDS INTERACTIVE FILL]"
    audience = _extract_section(md, ("audience", "users")) or "[NEEDS INTERACTIVE FILL]"
    constraints = _extract_section(md, ("constraint",)) or "[NEEDS INTERACTIVE FILL]"
    return (
        "# Project\n\n"
        f"## Name\n\n{name}\n\n"
        f"## Vision\n\n{vision}\n\n"
        f"## Audience\n\n{audience}\n\n"
        f"## Constraints\n\n{constraints}\n"
    )


# @spec FR-011: stacks/_default.md seed — .specs/features/012-brainstorm-ingestion/spec.md#fr-011
def seed_default_stack(profile_path: Path | None, today: str) -> str:
    """Build `.specs/stacks/_default.md` from `project-profile.md`.

    Marks the file as pending `/spec.stack` confirmation per FR-011.
    """
    body = "[NEEDS INTERACTIVE FILL]"
    if profile_path is not None and profile_path.exists():
        md = profile_path.read_text(encoding="utf-8")
        extracted = _extract_section(md, ("stack", "tech", "recommended"))
        if extracted:
            body = extracted
    return (
        f"---\nupdated: {today}\nstatus: Pending /spec.stack confirmation\n---\n\n"
        f"# Default Stack\n\n"
        "> Pending `/spec.stack` confirmation — review and adjust.\n\n"
        f"{body}\n"
    )

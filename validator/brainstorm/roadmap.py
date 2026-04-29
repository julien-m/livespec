"""Build `.specs/roadmap.md` populated by priority tier.

P1 → MVP, P2 or missing → Post-MVP, P3 → Future. Each item is checked
(`- [x]`) and links to its feature spec per FR-010 / AC-009.
"""

from __future__ import annotations

from .schemas import FlowFrontmatter, RoadmapOp


# @spec FR-010: Roadmap tiers — .specs/features/012-brainstorm-ingestion/spec.md#fr-010
def build_roadmap_op(
    flows: list[tuple[FlowFrontmatter, str, str]],
    target_path: str,
) -> RoadmapOp:
    """Bucket flows into MVP/Post-MVP/Future based on priority frontmatter.

    `flows` is a list of `(frontmatter, nnn, slug)` triples.
    """
    op = RoadmapOp(target_path=target_path)
    for fm, nnn, slug in flows:
        link = f"features/{nnn}-{slug}/spec.md"
        title = fm.title or slug
        priority = fm.priority
        if priority == "P1":
            op.mvp.append((title, link))
        elif priority == "P3":
            op.future.append((title, link))
        else:
            op.post_mvp.append((title, link))
    return op


def render_roadmap(op: RoadmapOp, today: str) -> str:
    """Render a `RoadmapOp` to a markdown string."""

    def _section(name: str, items: list[tuple[str, str]]) -> str:
        if not items:
            return f"## {name}\n\n_No features yet._\n"
        lines = [f"## {name}", ""]
        for title, link in items:
            lines.append(f"- [x] [{title}]({link})")
        lines.append("")
        return "\n".join(lines)

    return (
        f"# Roadmap\n\n"
        f"_Last updated: {today}_\n\n"
        f"{_section('MVP', op.mvp)}\n"
        f"{_section('Post-MVP', op.post_mvp)}\n"
        f"{_section('Future', op.future)}"
    )

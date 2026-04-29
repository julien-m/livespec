"""Unit tests for roadmap tier assignment."""

from __future__ import annotations

from validator.brainstorm.roadmap import build_roadmap_op, render_roadmap
from validator.brainstorm.schemas import FlowFrontmatter


def _fm(**kw: object) -> FlowFrontmatter:
    base: dict[str, object] = {
        "flow": "x",
        "title": "X",
        "status": "ready",
        "mockups": [],
        "surfaces": ["mobile"],
        "source": [],
        "generated_at": "2026-04-29",
    }
    base.update(kw)
    return FlowFrontmatter(**base)  # type: ignore[arg-type]


def test_p1_to_mvp() -> None:
    op = build_roadmap_op([(_fm(priority="P1", title="A"), "001", "a")], "roadmap.md")
    assert op.mvp == [("A", "features/001-a/spec.md")]
    assert not op.post_mvp
    assert not op.future


def test_p2_to_post_mvp() -> None:
    op = build_roadmap_op([(_fm(priority="P2", title="B"), "002", "b")], "roadmap.md")
    assert op.post_mvp == [("B", "features/002-b/spec.md")]


def test_missing_priority_to_post_mvp() -> None:
    op = build_roadmap_op([(_fm(priority=None, title="C"), "003", "c")], "roadmap.md")
    assert op.post_mvp == [("C", "features/003-c/spec.md")]


def test_p3_to_future() -> None:
    op = build_roadmap_op([(_fm(priority="P3", title="D"), "004", "d")], "roadmap.md")
    assert op.future == [("D", "features/004-d/spec.md")]


def test_render_includes_all_tiers() -> None:
    op = build_roadmap_op(
        [
            (_fm(priority="P1", title="A"), "001", "a"),
            (_fm(priority="P2", title="B"), "002", "b"),
            (_fm(priority="P3", title="C"), "003", "c"),
        ],
        "roadmap.md",
    )
    out = render_roadmap(op, "2026-04-29")
    assert "## MVP" in out
    assert "## Post-MVP" in out
    assert "## Future" in out
    assert "- [x] [A](features/001-a/spec.md)" in out

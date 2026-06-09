"""Tests for validator.hook_resolver (injection chain L0 → L1 → L2 → L3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.hook_resolver import (
    render_chain_for_stdout,
    render_template,
    resolve_injection_chain,
)
from validator.integrations import _reset_warnings_for_tests


@pytest.fixture(autouse=True)
def _clear_warning_dedup() -> None:
    _reset_warnings_for_tests()


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Absence-tolerance — everything missing → empty chain, no error
# ---------------------------------------------------------------------------


def test_all_levels_absent_returns_empty(tmp_path: Path) -> None:
    """Nothing on disk → empty chain, no exception, no stderr noise."""
    chain = resolve_injection_chain(
        "before",
        "plan",
        integrations_dir=tmp_path / "missing_l0",
        global_hooks_dir=tmp_path / "missing_global",
        project_root=tmp_path,
    )
    assert chain == []


def test_stdout_renderer_empty_on_absence(tmp_path: Path) -> None:
    assert (
        render_chain_for_stdout(
            "before",
            "plan",
            integrations_dir=tmp_path / "missing",
            global_hooks_dir=tmp_path / "missing2",
            project_root=tmp_path,
        )
        == ""
    )


# ---------------------------------------------------------------------------
# Level 0 injection
# ---------------------------------------------------------------------------


def test_level0_injected_before_higher_levels(tmp_path: Path) -> None:
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(
        l0_dir / "mockups.md",
        "---\nintegration: mockups\ncommands: [plan]\n---\nL0_BODY\n",
    )
    global_dir = tmp_path / "global"
    _write(global_dir / "before-plan.md", "L1_BODY\n")
    project_hooks = tmp_path / ".specs" / "hooks"
    _write(project_hooks / "before-plan.md", "L2_BODY\n")
    _write(project_hooks / "before-plan.local.md", "L3_BODY\n")

    chain = resolve_injection_chain(
        "before",
        "plan",
        integrations_dir=l0_dir,
        global_hooks_dir=global_dir,
        project_root=tmp_path,
    )
    assert len(chain) == 4
    assert "L0_BODY" in chain[0]
    assert "L1_BODY" in chain[1]
    assert "L2_BODY" in chain[2]
    assert "L3_BODY" in chain[3]


# ---------------------------------------------------------------------------
# Override scope semantics
# ---------------------------------------------------------------------------


def test_l3_override_does_not_strip_level_0(tmp_path: Path) -> None:
    """A `.local.md` override removes L1/L2 but NEVER L0."""
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(
        l0_dir / "x.md",
        "---\nintegration: x\ncommands: [plan]\n---\nL0\n",
    )
    global_dir = tmp_path / "global"
    _write(global_dir / "before-plan.md", "L1\n")
    project_hooks = tmp_path / ".specs" / "hooks"
    _write(project_hooks / "before-plan.md", "L2\n")
    _write(
        project_hooks / "before-plan.local.md",
        "---\nmode: override\n---\nL3_ALONE\n",
    )

    chain = resolve_injection_chain(
        "before",
        "plan",
        integrations_dir=l0_dir,
        global_hooks_dir=global_dir,
        project_root=tmp_path,
    )
    assert len(chain) == 2
    assert "L0" in chain[0]
    assert "L3_ALONE" in chain[1]
    # L1 / L2 were stripped
    assert all("L1" not in c for c in chain)
    assert all("L2" not in c for c in chain)


def test_l0_override_does_not_strip_higher_levels(tmp_path: Path) -> None:
    """A Level 0 override removes other L0 files but NEVER L1/L2/L3."""
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(l0_dir / "a.md", "---\nintegration: a\ncommands: [plan]\n---\nA\n")
    _write(
        l0_dir / "b.md",
        "---\nintegration: b\ncommands: [plan]\nmode: override\n---\nB\n",
    )
    global_dir = tmp_path / "global"
    _write(global_dir / "before-plan.md", "L1\n")

    chain = resolve_injection_chain(
        "before",
        "plan",
        integrations_dir=l0_dir,
        global_hooks_dir=global_dir,
        project_root=tmp_path,
    )
    assert len(chain) == 2
    assert "B" in chain[0]
    assert "L1" in chain[1]
    assert all("A\n" not in c for c in chain)


# ---------------------------------------------------------------------------
# Template variable rendering
# ---------------------------------------------------------------------------


def test_render_template_substitutes_known_keys() -> None:
    out = render_template(
        "Feature {{feature_name}} ({{feature_number}}) for {{stack}}.",
        {"feature_name": "001-foo", "feature_number": "001", "stack": "Next.js"},
    )
    assert out == "Feature 001-foo (001) for Next.js."


def test_render_template_leaves_unknown_literal() -> None:
    out = render_template("Hello {{unknown_var}}!", {"command": "plan"})
    assert out == "Hello {{unknown_var}}!"


def test_feature_ctx_resolved_in_chain(tmp_path: Path) -> None:
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(
        l0_dir / "x.md",
        "---\nintegration: x\ncommands: [plan]\n---\n"
        "Feature is {{feature_name}}; cmd is {{command}}.\n",
    )
    chain = resolve_injection_chain(
        "before",
        "plan",
        feature_ctx={"command": "plan", "feature_name": "042-test"},
        integrations_dir=l0_dir,
        global_hooks_dir=tmp_path / "global_missing",
        project_root=tmp_path,
    )
    assert chain
    assert "Feature is 042-test" in chain[0]
    assert "cmd is plan" in chain[0]


def test_unknown_template_vars_left_literal(tmp_path: Path) -> None:
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(
        l0_dir / "x.md",
        "---\nintegration: x\ncommands: [plan]\n---\n"
        "Path {{feature_path}}, num {{feature_number}}.\n",
    )
    chain = resolve_injection_chain(
        "before",
        "plan",
        feature_ctx={"command": "plan"},  # no feature_*
        integrations_dir=l0_dir,
        global_hooks_dir=tmp_path / "global_missing",
        project_root=tmp_path,
    )
    assert "{{feature_path}}" in chain[0]
    assert "{{feature_number}}" in chain[0]


# ---------------------------------------------------------------------------
# stdout renderer concatenation
# ---------------------------------------------------------------------------


def test_render_chain_for_stdout_concatenates_with_separator(tmp_path: Path) -> None:
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(l0_dir / "a.md", "---\nintegration: a\ncommands: [plan]\norder: 10\n---\nAAA\n")
    _write(l0_dir / "b.md", "---\nintegration: b\ncommands: [plan]\norder: 20\n---\nBBB\n")
    out = render_chain_for_stdout(
        "before",
        "plan",
        integrations_dir=l0_dir,
        global_hooks_dir=tmp_path / "missing",
        project_root=tmp_path,
    )
    assert "AAA" in out
    assert "BBB" in out
    assert "\n\n---\n\n" in out


# ---------------------------------------------------------------------------
# After phase isolation
# ---------------------------------------------------------------------------


def test_after_phase_does_not_pick_before_files(tmp_path: Path) -> None:
    l0_dir = tmp_path / "cfg"
    l0_dir.mkdir()
    _write(
        l0_dir / "x.md",
        "---\nintegration: x\ncommands: [plan]\nphase: before\n---\nBEFORE\n",
    )
    chain = resolve_injection_chain(
        "after",
        "plan",
        integrations_dir=l0_dir,
        global_hooks_dir=tmp_path / "missing",
        project_root=tmp_path,
    )
    assert chain == []


# ---------------------------------------------------------------------------
# Forward-compat: every documented template var has handler logic
# ---------------------------------------------------------------------------


def test_all_documented_template_vars_handled() -> None:
    """Parse system/hooks.md for every {{var}} and check the resolver knows them."""
    import re

    from validator.hook_resolver import _build_feature_ctx

    hooks_md = (Path(__file__).parent.parent / "system" / "hooks.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", hooks_md))

    ctx = _build_feature_ctx("plan", "042-foo", Path.cwd())
    # All documented vars must be either resolved or known to be left literal.
    # The hook resolver only handles the documented set:
    resolver_known = {
        "command",
        "feature_name",
        "feature_number",
        "feature_path",
        "stack",
        "project_name",
        # commit-hook variables documented in hooks.md but resolved elsewhere
        # (commit_context.py) — they are intentionally NOT resolved by the
        # general hook_resolver. We accept them as known-orphans.
        "spec_path",
        "plan_path",
        "adr_paths",
    }
    orphans = documented - resolver_known
    assert orphans == set(), f"undocumented {{var}} placeholders in hook_resolver: {orphans}"
    # Sanity: feature_name and command must resolve when feature_slug given.
    assert ctx["feature_name"] == "042-foo"
    assert ctx["command"] == "plan"

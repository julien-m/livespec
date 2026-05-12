"""Unit tests for validator/preview.py.

# @spec FR-006: render_preview
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-006
# @spec FR-007: placeholder resolver
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-007
# @spec AC-006: four project sources
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-006
# @spec AC-012: real feature slug substituted
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-012
"""

from __future__ import annotations

from pathlib import Path

from validator.expectations import parse_expectations
from validator.preview import (
    ProjectContext,
    build_project_context,
    render_preview,
    resolve_placeholders,
)


def _write_stack(project: Path, name: str = "Python 3.14 + Typer") -> None:
    stacks = project / ".specs" / "stacks"
    stacks.mkdir(parents=True, exist_ok=True)
    (stacks / "_default.md").write_text(f"# {name}\n", encoding="utf-8")


def _write_feature(project: Path, slug: str) -> None:
    fdir = project / ".specs" / "features" / slug
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "spec.md").write_text("# spec\n", encoding="utf-8")


def _write_screen(project: Path, name: str) -> None:
    screens = project / ".specs" / "design" / "screens"
    screens.mkdir(parents=True, exist_ok=True)
    (screens / f"{name}.png").write_bytes(b"\x89PNG\r\n")


def _write_conventions(project: Path, subdomains: list[str]) -> None:
    conv = project / ".conventions"
    conv.mkdir(parents=True, exist_ok=True)
    body = "subdomains:\n" + "\n".join(f"  - name: {s}" for s in subdomains) + "\n"
    (conv / "manifest.yaml").write_text(body, encoding="utf-8")


def test_build_context_all_sources(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_stack(project, "FastAPI + SQLite")
    _write_feature(project, "001-foo")
    _write_feature(project, "002-bar")
    _write_screen(project, "dashboard")
    _write_screen(project, "settings")
    _write_conventions(project, ["code", "design-tokens"])

    ctx = build_project_context(project)
    assert ctx.stack_name == "FastAPI + SQLite"
    assert ctx.feature_slugs == ["001-foo", "002-bar"]
    assert ctx.latest_feature == "002-bar"
    assert ctx.screen_names == ["dashboard", "settings"]
    assert ctx.convention_subdomains == ["code", "design-tokens"]
    assert ctx.notes == []


def test_build_context_missing_sources(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    ctx = build_project_context(project)
    assert ctx.stack_name is None
    assert ctx.feature_slugs == []
    assert ctx.screen_names == []
    assert ctx.convention_subdomains == []
    assert any("stack" in note for note in ctx.notes)
    assert any("features" in note for note in ctx.notes)
    assert any("screens" in note for note in ctx.notes)


def test_build_context_malformed_conventions(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    conv = project / ".conventions"
    conv.mkdir()
    (conv / "manifest.yaml").write_text("not: [valid yaml", encoding="utf-8")
    ctx = build_project_context(project)
    assert any("malformed" in note for note in ctx.notes)


def test_resolve_placeholders_all_tokens() -> None:
    ctx = ProjectContext(
        stack_name="Bun + Hono",
        feature_slugs=["001-foo", "002-bar"],
        screen_names=["dashboard"],
    )
    text = "Stack: <stack>; Feature: <feature>; Screen: <screen>; Path: <path>/x"
    out = resolve_placeholders(text, ctx)
    assert "Bun + Hono" in out
    assert "002-bar" in out  # latest feature
    assert "dashboard" in out
    assert "<path>" in out  # passthrough


def test_resolve_placeholders_missing_sources_use_fallbacks() -> None:
    ctx = ProjectContext()
    text = "<stack> / <feature> / <screen>"
    out = resolve_placeholders(text, ctx)
    assert "[no stack configured]" in out
    assert "[no features configured]" in out
    assert "[no screens configured]" in out


def test_render_preview_emits_markdown_with_substitutions(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_stack(project, "Demo Stack")
    _write_feature(project, "042-demo-feature")

    # Build a minimal but valid expectations file.
    body = _minimal_expectations("foo")
    exp_path = tmp_path / "foo.expectations.md"
    exp_path.write_text(body, encoding="utf-8")
    expectations = parse_expectations(exp_path)

    report = render_preview(expectations, project)
    assert "042-demo-feature" in report.markdown
    assert "Demo Stack" in report.markdown
    assert "<feature>" not in report.markdown  # all resolved
    assert report.command == "foo"


def _minimal_expectations(command: str) -> str:
    return f"""---
command: {command}
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.{command}

## 1. Purpose
demo.
## 2. Preconditions
- none.
## 3. Observable Signals
- "ok"
## 4. Filesystem Effects
- none.
## 5. Git Effects
- none.
## 6. Produced Artifacts
- none.
## 7. Exit Codes
| 0 | OK |
## 8. Outcome Matrix
- success.
## 9. Runtime Profile
- 1s.
## 10. Post-run Checks
- [ ] ok.
## 11. Troubleshooting
- none.
## 12. Verify Contract
```yaml
verify:
  must:
    - exit_code: 0
```

## 13. Demo Session

### Live Console Output
```
$ {command}
> running on <feature>
```
- line1
- line2

### Files Produced
- target: <feature>/spec.md
- log
- summary

### Aligned / Drift / Missing
- aligned: ok.
- drift: marker missing.
- missing: blocked.

### Runtime Profile (scenarios)
- cold: 1s
- warm: <1s
- worst: 2s

### Edge Cases
- a: noop.
- b: noop.
- c: noop.

### Post-run Actions
- success: done.
- drift: re-run.
- blocked: fix.
"""

# LiveSpec traceability anchors
# @spec(AC-010)
# @spec(AC-011)

"""Tests for the real ``validator/preview.py`` (render_preview + save_preview + CLI errors)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.expectations import parse_expectations
from validator.preview import render_preview, save_preview

runner = CliRunner()

EXPECTATIONS_WITH_PLACEHOLDERS = """\
---
command: spec-specify
contract_version: "1.0"
last_reviewed: 2026-06-10
---

# Expectations — /spec-specify

## 1. Purpose

Demo.

## 2. Preconditions

- nothing.

## 3. Observable Signals

**stdout must_contain:**
- "hello"

## 4. Filesystem Effects

**create:** none.

## 5. Git Effects

clean.

## 6. Produced Artifacts

- none.

## 7. Exit Codes

| Code | Meaning |
|------|---------|
| 0    | OK      |

## 8. Outcome Matrix

- success.

## 9. Runtime Profile

- 1-2 seconds.

## 10. Post-run Checks

- [ ] ok.

## 11. Troubleshooting

- _none_.

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
```

## 13. Demo Session

### Live Console Output

```
$ spec-specify on <stack>
> feature <feature>
> screen <screen>
```

### Files Produced

- .specs/features/<feature>/spec.md — new spec
- log.txt — execution log
- summary.md — human summary

### Aligned / Drift / Missing

- Aligned: every must rule passes, exit 0.
- Drift: a must rule fails, exit 1.
- Missing: precondition absent, exit 2.

### Runtime Profile (scenarios)

- Cold run: 1-2 seconds.
- Warm run: < 1 second.
- Worst case: 5 seconds.

### Edge Cases

- Empty input: produces an empty output.
- Malformed input: surfaces a clear error.
- Concurrent runs: serialized.

### Post-run Actions

- On success: review spec.md.
- On drift: inspect the report.
- On blocked: restore preconditions.
"""


def make_project(
    tmp_path: Path,
    *,
    with_stack: bool = True,
    with_features: bool = True,
    with_screens: bool = True,
    with_conventions: bool = True,
) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir(exist_ok=True)
    if with_stack:
        (specs / "stacks").mkdir(parents=True, exist_ok=True)
        (specs / "stacks" / "_default.md").write_text(
            "---\ntitle: Default Stack\n---\n\n# Stack — DemoStack\n\n| Layer | Choice |\n",
            encoding="utf-8",
        )
    if with_features:
        for slug in ("001-first", "012-latest"):
            (specs / "features" / slug).mkdir(parents=True, exist_ok=True)
    if with_screens:
        screens = specs / "design" / "screens"
        screens.mkdir(parents=True, exist_ok=True)
        (screens / "dashboard.png").write_bytes(b"\x89PNG")
    if with_conventions:
        conventions = tmp_path / ".conventions"
        conventions.mkdir(exist_ok=True)
        (conventions / "manifest.yaml").write_text(
            "domains:\n  code:\n    sources: []\n  design-tokens:\n    sources: []\n",
            encoding="utf-8",
        )
    return tmp_path


def parse_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "expectations.md"
    path.write_text(EXPECTATIONS_WITH_PLACEHOLDERS, encoding="utf-8")
    return path


class TestRenderPreview:
    def test_substitutes_from_all_four_sources(self, tmp_path: Path) -> None:
        project = make_project(tmp_path)
        expectations = parse_expectations(parse_fixture(tmp_path))
        markdown = render_preview(expectations, project)
        assert "DemoStack" in markdown
        assert "012-latest" in markdown
        assert "dashboard.png" in markdown
        assert "design-tokens" in markdown
        # Resolvable placeholders must not leak raw.
        assert "<feature>" not in markdown
        assert "<screen>" not in markdown
        assert "<stack>" not in markdown

    def test_feature_placeholder_resolves_to_latest_slug(self, tmp_path: Path) -> None:
        project = make_project(tmp_path)
        expectations = parse_expectations(parse_fixture(tmp_path))
        markdown = render_preview(expectations, project)
        assert "feature 012-latest" in markdown

    def test_partial_sources_render_not_configured(self, tmp_path: Path) -> None:
        project = make_project(tmp_path, with_screens=False, with_conventions=False)
        expectations = parse_expectations(parse_fixture(tmp_path))
        markdown = render_preview(expectations, project)
        # EC-009: missing sources annotate; others still resolve.
        assert "[not configured]" in markdown
        assert "DemoStack" in markdown
        assert "012-latest" in markdown
        assert "<screen>" not in markdown

    def test_empty_screens_directory_not_configured(self, tmp_path: Path) -> None:
        project = make_project(tmp_path, with_screens=False)
        screens = project / ".specs" / "design" / "screens"
        screens.mkdir(parents=True)
        expectations = parse_expectations(parse_fixture(tmp_path))
        markdown = render_preview(expectations, project)
        assert "[not configured]" in markdown


class TestSavePreview:
    def test_save_writes_previews_file(self, tmp_path: Path) -> None:
        project = make_project(tmp_path)
        expectations = parse_expectations(parse_fixture(tmp_path))
        markdown = render_preview(expectations, project)
        saved = save_preview(markdown, "spec-specify", project)
        assert saved.parent == project / ".specs" / ".previews"
        assert saved.name.startswith("spec-specify-")
        assert saved.suffix == ".md"
        assert saved.read_text(encoding="utf-8") == markdown


@pytest.fixture
def cli_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project = make_project(tmp_path)
    override_dir = project / ".specs" / "expectations"
    override_dir.mkdir(parents=True)
    (override_dir / "spec-specify.md").write_text(EXPECTATIONS_WITH_PLACEHOLDERS, encoding="utf-8")
    monkeypatch.chdir(project)
    return project


class TestPreviewCli:
    def test_preview_exits_0_with_real_values(self, cli_project: Path) -> None:
        result = runner.invoke(app, ["verify-output", "specify", "--preview"])
        assert result.exit_code == 0, result.output
        assert "012-latest" in result.output
        assert "DemoStack" in result.output

    def test_preview_save_writes_file_matching_stdout(self, cli_project: Path) -> None:
        result = runner.invoke(app, ["verify-output", "specify", "--preview", "--save"])
        assert result.exit_code == 0, result.output
        previews = list((cli_project / ".specs" / ".previews").glob("spec-specify-*.md"))
        assert len(previews) == 1
        assert previews[0].read_text(encoding="utf-8") in result.output

    def test_preview_without_save_writes_nothing(self, cli_project: Path) -> None:
        result = runner.invoke(app, ["verify-output", "specify", "--preview"])
        assert result.exit_code == 0, result.output
        assert not (cli_project / ".specs" / ".previews").exists()

    def test_section_13_missing_exits_2(self, cli_project: Path) -> None:
        truncated = EXPECTATIONS_WITH_PLACEHOLDERS.split("## 13. Demo Session")[0]
        (cli_project / ".specs" / "expectations" / "spec-specify.md").write_text(
            truncated, encoding="utf-8"
        )
        result = runner.invoke(app, ["verify-output", "specify", "--preview"])
        assert result.exit_code == 2
        assert "section 13 missing in" in result.output

    def test_empty_subsection_exits_2(self, cli_project: Path) -> None:
        gutted = EXPECTATIONS_WITH_PLACEHOLDERS.replace(
            "- On success: review spec.md.\n- On drift: inspect the report.\n"
            "- On blocked: restore preconditions.\n",
            "",
        )
        (cli_project / ".specs" / "expectations" / "spec-specify.md").write_text(
            gutted, encoding="utf-8"
        )
        result = runner.invoke(app, ["verify-output", "specify", "--preview"])
        assert result.exit_code == 2
        assert "section 13 sub-section 'Post-run Actions' is empty" in result.output

    def test_no_specs_directory_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        result = runner.invoke(app, ["verify-output", "specify", "--preview"])
        assert result.exit_code == 2
        assert "preview requires a LiveSpec project (no .specs/ found)" in result.output

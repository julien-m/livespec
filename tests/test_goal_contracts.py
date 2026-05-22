"""Tests for deterministic command goal contracts.

# @spec FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-013, FR-014, FR-015
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

from pathlib import Path

from validator.goal_contracts import (
    compile_command_goal,
    normalize_goal_flags,
    render_goal_objective,
)

EXPECTATIONS = """\
---
command: spec-demo
contract_version: "1.0"
last_reviewed: 2026-05-21
---

# Expectations — /spec-demo

## 1. Purpose

Demo command.

## 2. Preconditions

- `.specs/project.md` exists.

## 3. Observable Signals

- "done"

## 4. Filesystem Effects

- creates demo.txt.

## 5. Git Effects

- none.

## 6. Produced Artifacts

- demo.txt.

## 7. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | success |

## 8. Outcome Matrix

- success.

## 9. Runtime Profile

- <1s.

## 10. Post-run Checks

- [ ] output checked.

## 11. Troubleshooting

- rerun.

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "done"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--strict"
      must:
        - exists: "demo.txt"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-demo
> done
```
- line a
- line b
- line c

### Files Produced

- demo.txt
- report.md
- summary.md

### Aligned / Drift / Missing

- aligned: done.
- drift: marker missing.
- missing: no artifact.

### Runtime Profile

- cold: <1s.
- warm: <1s.
- worst: 2s.

### Edge Cases

- missing file: blocked.
- bad output: drift.
- crash: error.

### Post-run Actions

- success: continue.
- drift: inspect output.
- blocked: restore artifact.
"""

SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Definition of Done (Command-Level)

`/spec-demo` is complete only if all are true:

- [ ] `demo.txt` exists
- [ ] Output contains `done`
- [ ] No traceback was emitted

If any item fails, fix before returning final output.
"""


def _fixture_roots(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "project"
    livespec_root = tmp_path / "livespec"
    (project_root / ".specs").mkdir(parents=True)
    skill_dir = livespec_root / ".agent-sync" / "skills" / "spec-demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "expectations.md").write_text(EXPECTATIONS, encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(SKILL, encoding="utf-8")
    return project_root, livespec_root


def _write_conventions(project_root: Path, ai_root: Path) -> None:
    conventions = project_root / ".conventions"
    conventions.mkdir()
    (conventions / "index.md").write_text(
        f"""\
# Conventions · fixture

> `$AIRESOURCES` = `{ai_root.as_posix()}`

## code [code, tests, logging, naming, imports, architecture]
→ $AIRESOURCES/code-conventions/general.md, python.md

## design-tokens [CSS, colors, spacing, typography, mockup, UI, visual]
→ $AIRESOURCES/design/tokens.md
""",
        encoding="utf-8",
    )
    (ai_root / "code-conventions").mkdir(parents=True)
    (ai_root / "design").mkdir(parents=True)
    (ai_root / "code-conventions" / "general.md").write_text(
        "# General\n- Prefer explicit typed APIs.\n",
        encoding="utf-8",
    )
    (ai_root / "code-conventions" / "python.md").write_text(
        "# Python\n- Use pytest for tests.\n",
        encoding="utf-8",
    )
    (ai_root / "design" / "tokens.md").write_text(
        "# Tokens\n- Use spacing tokens for mockups.\n",
        encoding="utf-8",
    )


def test_normalize_goal_flags_is_order_independent_and_preserves_values() -> None:
    assert normalize_goal_flags("--strict --priority P1 --auto") == [
        "--auto",
        "--priority=P1",
        "--strict",
    ]
    assert normalize_goal_flags(["--priority=P1", "--auto", "--strict"]) == [
        "--auto",
        "--priority=P1",
        "--strict",
    ]


def test_compile_command_goal_is_reproducible_for_same_inputs(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)

    rendered = [
        compile_command_goal(
            "demo",
            project_root=project_root,
            livespec_root=livespec_root,
            feature="052-deterministic-command-goal-contracts",
            flags="--strict --priority P1 --auto",
        )
        for _ in range(10)
    ]

    first = rendered[0]
    assert all(goal.canonical_json == first.canonical_json for goal in rendered)
    assert all(goal.goal_hash == first.goal_hash for goal in rendered)
    assert first.payload["normalized_flags"] == [
        "--auto",
        "--priority=P1",
        "--strict",
    ]
    assert first.payload["expectation_sections"]["filesystem_effects"] == [
        "- creates demo.txt."
    ]
    assert first.payload["expectation_sections"]["post_run_checks"] == [
        "- [ ] output checked."
    ]
    assert "timestamp" not in first.canonical_json.lower()


def test_compile_command_goal_embeds_code_convention_domains(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")

    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags="--strict",
    )

    conventions = goal.payload["conventions"]
    assert conventions["index_path"] == ".conventions/index.md"
    assert [domain["name"] for domain in conventions["selected_domains"]] == ["code"]
    assert conventions["selected_domains"][0]["source_files"] == [
        {
            "path": "$AIRESOURCES/code-conventions/general.md",
            "sha256": conventions["selected_domains"][0]["source_files"][0]["sha256"],
            "content": "# General\n- Prefer explicit typed APIs.",
        },
        {
            "path": "$AIRESOURCES/code-conventions/python.md",
            "sha256": conventions["selected_domains"][0]["source_files"][1]["sha256"],
            "content": "# Python\n- Use pytest for tests.",
        },
    ]


def test_compile_command_goal_adds_design_domain_for_ui_feature(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    feature_dir = project_root / ".specs" / "features" / "002-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# UI Feature\n\nBuild a mockup-driven visual screen with spacing tokens.",
        encoding="utf-8",
    )

    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="002-ui",
        flags="--visual",
    )

    selected = goal.payload["conventions"]["selected_domains"]
    assert [domain["name"] for domain in selected] == ["code", "design-tokens"]
    assert "design-tokens" in goal.objective
    assert "$AIRESOURCES/design/tokens.md" in goal.objective


def test_compile_command_goal_extracts_definition_of_done(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags=[],
    )

    assert goal.payload["definition_of_done"] == [
        "`demo.txt` exists",
        "Output contains `done`",
        "No traceback was emitted",
    ]
    assert goal.payload["expectations"]["source_path"].endswith(
        ".agent-sync/skills/spec-demo/expectations.md"
    )


def test_render_goal_objective_is_stable_text_from_payload(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags="--strict",
    )

    objective = render_goal_objective(goal)

    assert objective == render_goal_objective(goal)
    assert "Goal hash:" in objective
    assert "Command: spec-demo" in objective
    assert "- `demo.txt` exists" in objective
    assert "Filesystem effects:" in objective
    assert "- creates demo.txt." in objective
    assert "- must contains: done" in objective


def test_anti_drift_block_documents_shared_goal_protocol() -> None:
    """AC-007: all imported command protocols share the same goal lifecycle."""
    text = Path("system/anti-drift-block.md").read_text(encoding="utf-8")

    assert "livespec goal render <command-name>" in text
    assert "livespec goal verify <command-name>" in text
    assert "/goal hash:<" in text  # Exact /goal slash command form with hash+ref
    assert "/goal clear" in text  # Active goal precheck
    assert "already active" in text  # Precheck documentation

# LiveSpec Python Commit Hook & Orchestration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable commit hook with enriched `/git.commit --intent` invocation and structural Python validation gates (Branch 1), then add Python CLI modules for deterministic pipeline state management and git operations (Branch 2).

**Architecture:** Branch 1 modifies 4 Markdown command/system files. Branch 2 forks from Branch 1 (not main) to avoid conflicts on shared files, then extends `validator/` with 3 new Typer command groups.

**Tech Stack:** Python 3.11, Typer, subprocess, pathlib, re, json — all already in project deps.

---

## File Map

### Branch 1 — Modifications only

| File | Change |
|---|---|
| `system/hooks.md` | Add `## Commit Hook` section |
| `commands/feature.md` | Replace auto-commit raw git call with hook-resolution flow |
| `commands/specify.md` | Add structural validation gate after spec.md generation |
| `commands/plan.md` | Add structural validation gate after plan.md generation |

### Branch 2 — New files + modifications

| File | Change |
|---|---|
| `validator/specs_utils.py` | **NEW** — `find_specs_root()` extracted from cli.py |
| `validator/pipeline.py` | **NEW** — Typer app: `init`, `update`, `read`, `next` |
| `validator/git_ops.py` | **NEW** — Typer app: `branch`, `stage`, `merge`, `delete`, `status` |
| `validator/commit_context.py` | **NEW** — Typer app: `write`, `read`, `clear` |
| `validator/cli.py` | Delegate `_find_specs_root` → `specs_utils`; register 3 new groups |
| `tests/test_pipeline.py` | **NEW** |
| `tests/test_git_ops.py` | **NEW** |
| `tests/test_commit_context.py` | **NEW** |
| `commands/feature.md` | Replace all pipeline.md writes + git staging with Python CLI calls |
| `commands/ship.md` | Replace raw git branch/merge/delete with `livespec git` calls |
| `system/hooks.md` | Add gitignore note for `.commit-context.json` |
| `.gitignore` | Add `.specs/hooks/.commit-context.json` |

---

## BRANCH 1: feature/python-commit-hook

### Task 1: Create Branch 1

- [ ] **Step 1:** `git checkout -b feature/python-commit-hook`

---

### Task 2: Add Commit Hook Section to system/hooks.md

**Files:**
- Modify: `system/hooks.md`

- [ ] **Step 1:** Read `system/hooks.md` lines 200–289 to find insertion point (before `## Template Variables`)

- [ ] **Step 2:** Insert before `## Template Variables`:

```markdown
---

## Commit Hook

The `commit` hook is a special hook type that controls how LiveSpec performs git commits during auto-commit pipelines. Unlike lifecycle hooks (before/after), it defines the commit action itself.

### Naming

```
commit.md           # team-shared (committed)
commit.local.md     # personal (gitignored)
```

No `before-`/`after-` prefix — this hook IS the action.

### Resolution (3 levels)

```
Level 1: ~/.claude/livespec/hooks/commit.md     (global — all projects)
Level 2: .specs/hooks/commit.md                 (project — committed)
Level 3: .specs/hooks/commit.local.md           (personal — gitignored)
```

Same inheritance model as all other hooks (`mode: extend` or `mode: override` in frontmatter).

### Template Variables

| Variable | Resolved value |
|---|---|
| `{{spec_path}}` | Absolute path to `spec.md` for the current feature |
| `{{plan_path}}` | Absolute path to `plan.md` for the current feature |
| `{{adr_paths}}` | Comma-separated absolute paths matching `.specs/stacks/decisions/ADR-*.md` (empty string if none) |
| `{{feature_name}}` | Full kebab directory name (e.g., `003-notifications`) |
| `{{feature_number}}` | Numeric prefix only (e.g., `003`) |

`{{adr_paths}}` glob root: `{project_root}/.specs/stacks/decisions/`

### Fallback

If no `commit.md` exists at any level → invoke `/git.commit` without `--intent`.

**Never use bare `git commit`** — blocked by `commit-via-skill.md`.

### Example Global Hook (`~/.claude/livespec/hooks/commit.md`)

```markdown
---
mode: override
---

Use `/git.commit "feat({{feature_name}}): <message>" --intent "implements {{feature_name}} — spec: {{spec_path}}, plan: {{plan_path}}, ADRs: {{adr_paths}}"` to commit.

If {{adr_paths}} is empty, use: `/git.commit "feat({{feature_name}}): <message>" --intent "implements {{feature_name}} — spec: {{spec_path}}, plan: {{plan_path}}"`
```

### Gitignore

`.specs/hooks/commit.local.md` is already covered by the existing `.specs/hooks/*.local.md` pattern.

`.specs/hooks/.commit-context.json` (used in Branch 2) must be added separately — see Branch 2 notes.
```

- [ ] **Step 3:** Re-read `system/hooks.md` to verify `## Commit Hook` appears before `## Template Variables`

---

### Task 3: Update commands/feature.md — Auto-Commit Phase

**Files:**
- Modify: `commands/feature.md`

- [ ] **Step 1:** Read `commands/feature.md` lines 285–302 to confirm exact current auto-commit text

- [ ] **Step 2:** Find and replace the entire `## Auto-Commit` section. Replace:

```markdown
## Auto-Commit (`--auto` only)

When `--auto` is active and Phase 3.5 (Test) completes successfully:

1. Run `/audit` — if fail, attempt fix (max 3 retries). If still failing → abort (no commit)
2. Verify all tests pass
3. Stage all changes: spec, plan, implementation, progress, changelogs, roadmap updates
4. Commit with message: `feat(NNN-feature-name): <short description>`
5. Update `pipeline.md`: all phases → `Done`

**Without `--auto`:** no commit is made. The user commits manually.
```

With:

```markdown
## Auto-Commit (`--auto` only)

When `--auto` is active and Phase 3.5 (Test) completes successfully:

1. Run `/audit` — if fail, attempt fix (max 3 retries). If still failing → abort (no commit)
2. Verify all tests pass
3. Stage all changes: spec, plan, implementation, progress, changelogs, roadmap updates

4. **Resolve commit hook** from 3 levels (global → project → local), applying inheritance rules from `system/hooks.md`:
   - `~/.claude/livespec/hooks/commit.md`
   - `.specs/hooks/commit.md`
   - `.specs/hooks/commit.local.md`

5. **Resolve template variables** before injecting hook content:
   - `{{spec_path}}` → absolute path to `.specs/features/NNN-feature-name/spec.md`
   - `{{plan_path}}` → absolute path to `.specs/features/NNN-feature-name/plan.md`
   - `{{adr_paths}}` → comma-separated results of glob `.specs/stacks/decisions/ADR-*.md` from project root (empty string if no files match)
   - `{{feature_name}}` → full feature directory name (e.g., `003-notifications`)
   - `{{feature_number}}` → numeric prefix only (e.g., `003`)

6. **If commit hook found:** inject resolved hook content into context, follow its instructions (e.g., invoke `/git.commit "feat({{feature_name}}): <message>" --intent "implements {{feature_name}} — spec: {{spec_path}}, plan: {{plan_path}}, ADRs: {{adr_paths}}"`)

7. **If no commit hook at any level:** invoke `/git.commit` without `--intent` (standard commit with Codex audit, no implementation intent)

8. Update `pipeline.md`: all phases → `Done`

> **Note (Branch 2):** When the Python pipeline orchestrator is active, step 8 is replaced by `livespec pipeline update` calls and staging is handled by `livespec git stage`. The hook resolution in steps 4–7 remains identical.

**Without `--auto`:** no commit is made. The user commits manually.
```

- [ ] **Step 3:** Re-read `commands/feature.md` lines 285–320 to confirm the new auto-commit section is in place

---

### Task 4: Add Structural Validation Gate to commands/specify.md

**Files:**
- Modify: `commands/specify.md`

- [ ] **Step 1:** Read `commands/specify.md` lines 155–170 to locate the "after spec.md generation" position

- [ ] **Step 2:** After the spec.md generation step, insert:

```markdown
### Structural Validation

After generating `spec.md`, validate its structure before presenting to the user:

```bash
livespec validate .specs/features/NNN-feature-name/spec.md --format compact
```

**Exit 0 — validation passed:** proceed to the next step.

**Exit non-zero — validation failed:**

Inject the verbatim `livespec validate` output as a hard constraint for regeneration:

> "The spec.md you just generated failed structural validation. Regenerate spec.md fixing these issues exactly as listed:
> `<livespec validate --format compact output verbatim>`"

Regenerate `spec.md` from scratch (original feature description + constitution + stack + error constraints). Increment retry counter.

**Maximum 2 retries.** On 3rd failure:
```
ABORT: "spec.md failed structural validation after 2 retries.
        Last errors: <livespec validate output>
        Fix manually then re-run /spec.specify."
```
```

- [ ] **Step 3:** Re-read edited section to confirm gate is positioned after generation and before gate/presentation step

---

### Task 5: Add Structural Validation Gate to commands/plan.md

**Files:**
- Modify: `commands/plan.md`

- [ ] **Step 1:** Read `commands/plan.md` lines 310–370 to locate where `plan.md` is generated

- [ ] **Step 2:** After the plan.md generation step, insert same gate pattern:

```markdown
### Structural Validation

After generating `plan.md`, validate its structure:

```bash
livespec validate .specs/features/NNN-feature-name/plan.md --format compact
```

**Exit 0:** proceed to plan gate.

**Exit non-zero:** inject verbatim errors:

> "The plan.md you just generated failed structural validation. Regenerate plan.md fixing these issues:
> `<livespec validate --format compact output verbatim>`"

Regenerate `plan.md` (spec.md + constitution + stack + error constraints). **Maximum 2 retries.** On 3rd failure:
```
ABORT: "plan.md failed structural validation after 2 retries.
        Last errors: <livespec validate output>"
```
```

- [ ] **Step 3:** Re-read to verify gate is before plan gate/approval step

---

### Task 6: Integration Test (manual CLI verification only)

- [ ] **Step 1:** `pip install -e /Users/julienm/projects/livespec --quiet`

- [ ] **Step 2:** `livespec validate <path-to-existing-spec.md> --format compact` — verify exit code and output format

- [ ] **Step 3:** Create sample hook: `mkdir -p ~/.claude/livespec/hooks && cat > ~/.claude/livespec/hooks/commit.md` with sample override content — verify file exists and is well-formed

- [ ] **Note:** Hook resolution logic lives in Markdown and is not CLI-automatable; verify structure manually during code review

---

### Task 7: Commit Branch 1

- [ ] **Step 1:** Stage all Branch 1 files:

```bash
cd /Users/julienm/projects/livespec
git add system/hooks.md commands/feature.md commands/specify.md commands/plan.md
```

- [ ] **Step 2:** Verify clean: `git status` shows only those 4 files staged, no other dirty state

- [ ] **Step 3:** Invoke `/git.commit` with message: `feat(pipeline): add configurable commit hook and structural validation gates`

- [ ] **Gate:** Do NOT proceed to Task 8 until `git status` confirms clean working tree on `feature/python-commit-hook`

---

## BRANCH 2: feature/python-pipeline-orchestration

---

### Task 8: Create Branch 2 off Branch 1

- [ ] **Precondition:** Verify `git status` on `feature/python-commit-hook` is clean (Task 7 gate passed)

- [ ] **Step 1:**
```bash
cd /Users/julienm/projects/livespec
git checkout feature/python-commit-hook
git checkout -b feature/python-pipeline-orchestration
```

- [ ] **Step 2:** Verify: `git log --oneline -3` shows Branch 1 commit at HEAD

---

### Task 9: Refactor cli.py — Extract find_specs_root FIRST

**Do this before creating any new module. Establishes the single source of truth.**

**Files:**
- Create: `validator/specs_utils.py`
- Modify: `validator/cli.py`

- [ ] **Step 1:** Re-read `validator/cli.py` lines 1–45 to see current `_find_specs_root` implementation

- [ ] **Step 2:** Create `validator/specs_utils.py`:

```python
# validator/specs_utils.py
"""Shared utility for finding the .specs/ root directory."""

from __future__ import annotations

from pathlib import Path

from .exceptions import SpecsRootNotFoundError


def find_specs_root(start: Path | None = None) -> Path:
    """Find the .specs/ directory starting from the given path or cwd.

    Args:
        start: Starting path to search from, or None for cwd.

    Returns:
        Path to the .specs/ directory.

    Raises:
        SpecsRootNotFoundError: If .specs/ cannot be found.
    """
    search = start or Path.cwd()
    if search.is_file():
        search = search.parent
    for parent in [search, *search.parents]:
        if parent.name == ".specs":
            return parent
        specs_dir = parent / ".specs"
        if specs_dir.is_dir():
            return specs_dir
    raise SpecsRootNotFoundError(str(search))
```

- [ ] **Step 3:** Edit `validator/cli.py`: add `from . import specs_utils` to imports, then replace `_find_specs_root` function body with `return specs_utils.find_specs_root(start)` (keep `_require_specs_root` wrapper unchanged)

- [ ] **Step 4:** Run existing tests to verify no regression:

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/ -x -q --ignore=tests/integration 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 5:** `livespec --help` works

---

### Task 10: Create validator/pipeline.py (TDD)

**Files:**
- Create: `validator/pipeline.py`
- Create: `tests/test_pipeline.py`
- Modify: `validator/cli.py` (temporary registration)

**Constants:**

```python
PHASE_ORDER = ["specify", "spec-review", "plan", "plan-review", "preflight", "implement", "test"]

PHASE_MAP = {
    "specify": "Specify",
    "spec-review": "Spec Review",
    "plan": "Plan",
    "plan-review": "Plan Review",
    "preflight": "Preflight",
    "implement": "Implement",
    "test": "Test",
}

STATUS_MAP = {
    "pending": "Pending",
    "in_progress": "In Progress",
    "done": "Done",
    "skipped": "Skipped",
    "blocked": "Blocked",
}

DONE_STATUSES = {"Done", "Skipped"}
```

**Exit codes (must be documented in `--help` strings):**
- `pipeline next`: exit 0 = found next phase (prints slug to stdout); exit 2 = all phases Done/Skipped (pipeline complete — callers must treat as success, not error); exit 1 = pipeline.md missing or parse failure

**`update` implementation contract:**
- Build the replacement row: `f"| {display_phase} | {display_status} | {timestamp} |"`
- Match pattern (flexible whitespace): `re.compile(r"\|[^|]*\b" + re.escape(display_phase) + r"\b[^|]*\|[^|]*\|[^|]*\|")`
- Use `re.sub(pattern, new_row, content, count=1)`
- If content unchanged after sub (no match): print error to stderr, exit 1 — never silently exit 0 on no-op write
- Write result atomically (write to `.tmp` then `Path.rename()`)

- [ ] **Step 1:** Create `tests/test_pipeline.py`:

```python
"""Tests for validator.pipeline — pipeline state management CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()

PIPELINE_MD = """\
# Pipeline — 001-test

**Started:** 2026-04-10 12:00
**Flags:** none

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Pending | — |
| Spec Review | Pending | — |
| Plan | Pending | — |
| Plan Review | Pending | — |
| Preflight | Pending | — |
| Implement | Pending | — |
| Test | Pending | — |
"""

PIPELINE_MD_PADDED = """\
# Pipeline — 001-test

**Started:** 2026-04-10 12:00
**Flags:** none

| Phase | Status | Completed At |
|-------|--------|--------------|
|  Specify  |  Pending  |  —  |
|  Spec Review  |  Pending  |  —  |
|  Plan  |  Pending  |  —  |
|  Plan Review  |  Pending  |  —  |
|  Preflight  |  Pending  |  —  |
|  Implement  |  Pending  |  —  |
|  Test  |  Pending  |  —  |
"""


@pytest.fixture()
def specs_root(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    feature_dir = specs / "features" / "001-test"
    feature_dir.mkdir(parents=True)
    return specs


class TestPipelineInit:
    def test_creates_pipeline_md(self, specs_root: Path) -> None:
        feature_dir = specs_root / "features" / "001-test"
        result = runner.invoke(app, ["pipeline", "init", "--feature", "001-test"], catch_exceptions=False)
        assert result.exit_code == 0
        pipeline = feature_dir / "pipeline.md"
        assert pipeline.exists()
        content = pipeline.read_text()
        for phase in ["Specify", "Spec Review", "Plan", "Plan Review", "Preflight", "Implement", "Test"]:
            assert f"| {phase} | Pending |" in content

    def test_error_if_feature_not_found(self, specs_root: Path) -> None:
        result = runner.invoke(app, ["pipeline", "init", "--feature", "999-nonexistent"])
        assert result.exit_code != 0


class TestPipelineUpdate:
    def test_update_sets_status(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        result = runner.invoke(
            app,
            ["pipeline", "update", "--feature", "001-test", "--phase", "specify", "--status", "in_progress"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "In Progress" in pipeline_path.read_text()

    def test_update_padded_table_rows(self, specs_root: Path) -> None:
        """AI-generated tables may have extra whitespace padding around cell values."""
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD_PADDED)
        result = runner.invoke(
            app,
            ["pipeline", "update", "--feature", "001-test", "--phase", "specify", "--status", "done"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Done" in pipeline_path.read_text()

    def test_update_is_idempotent(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        runner.invoke(app, ["pipeline", "update", "--feature", "001-test", "--phase", "specify", "--status", "done"])
        content_after_first = pipeline_path.read_text()
        runner.invoke(app, ["pipeline", "update", "--feature", "001-test", "--phase", "specify", "--status", "done"])
        assert pipeline_path.read_text() == content_after_first

    def test_update_unknown_phase_exits_1(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        result = runner.invoke(
            app,
            ["pipeline", "update", "--feature", "001-test", "--phase", "nonexistent", "--status", "done"],
        )
        assert result.exit_code != 0
        assert pipeline_path.read_text() == PIPELINE_MD  # File must not be mutated


class TestPipelineRead:
    def test_outputs_json_for_all_phases(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        result = runner.invoke(app, ["pipeline", "read", "--feature", "001-test"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data.keys()) == {"specify", "spec-review", "plan", "plan-review", "preflight", "implement", "test"}
        assert data["specify"] == "Pending"


class TestPipelineNext:
    def test_returns_first_pending_exits_0(self, specs_root: Path) -> None:
        content = PIPELINE_MD.replace("| Specify | Pending |", "| Specify | Done |")
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(content)
        result = runner.invoke(app, ["pipeline", "next", "--feature", "001-test"], catch_exceptions=False)
        assert result.exit_code == 0
        assert result.output.strip() == "spec-review"

    def test_all_done_exits_2(self, specs_root: Path) -> None:
        """Exit 2 = pipeline complete (success state, not error)."""
        content = PIPELINE_MD
        for phase in ["Specify", "Spec Review", "Plan", "Plan Review", "Preflight", "Implement", "Test"]:
            content = content.replace(f"| {phase} | Pending |", f"| {phase} | Done |")
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(content)
        result = runner.invoke(app, ["pipeline", "next", "--feature", "001-test"])
        assert result.exit_code == 2  # NOT 1 — all done is a success state

    def test_missing_pipeline_exits_1(self, specs_root: Path) -> None:
        result = runner.invoke(app, ["pipeline", "next", "--feature", "001-test"])
        assert result.exit_code == 1
```

- [ ] **Step 2:** Run tests → confirm FAIL

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/test_pipeline.py -v 2>&1 | head -30
```

- [ ] **Step 3:** Create `validator/pipeline.py` implementing the contract above (PHASE_MAP, STATUS_MAP, DONE_STATUSES, init/update/read/next with exit code semantics documented in --help strings)

- [ ] **Step 4:** Add temporarily to `validator/cli.py`:

```python
from .pipeline import pipeline_app
app.add_typer(pipeline_app, name="pipeline")
```

- [ ] **Step 5:** Run tests → PASS

```bash
python -m pytest tests/test_pipeline.py -v
```

---

### Task 11: Create validator/git_ops.py (TDD)

**Files:**
- Create: `validator/git_ops.py`
- Create: `tests/test_git_ops.py`
- Modify: `validator/cli.py` (temporary registration)

**Implementation contract:**
- All commands: `subprocess.run(check=False)` — never raise on non-zero exit
- `merge`: on conflict (CONFLICT in stdout+stderr) → attempt `git merge --abort`; **whether abort succeeds or fails, always exit 2** — log abort result to stderr but do not change exit code
- `delete`: "not fully merged" in stderr → exit 2 (distinct); other error → exit 1

- [ ] **Step 1:** Create `tests/test_git_ops.py`:

```python
"""Tests for validator.git_ops — git CLI operations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    specs = tmp_path / ".specs"
    specs.mkdir()
    feature_dir = specs / "features" / "001-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# spec")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


class TestGitBranch:
    def test_creates_branch(self, git_repo: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(app, ["git", "branch", "feature/test-branch"], catch_exceptions=False)
            assert result.exit_code == 0
            check = subprocess.run(["git", "branch", "--show-current"], cwd=git_repo, capture_output=True, text=True)
            assert check.stdout.strip() == "feature/test-branch"
        finally:
            os.chdir(original)

    def test_already_exists_exits_1(self, git_repo: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            runner.invoke(app, ["git", "branch", "feature/dup"])
            result = runner.invoke(app, ["git", "branch", "feature/dup"])
            assert result.exit_code == 1
        finally:
            os.chdir(original)


class TestGitStage:
    def test_stages_feature_files(self, git_repo: Path) -> None:
        import os
        (git_repo / ".specs" / "features" / "001-test" / "plan.md").write_text("# plan")
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(app, ["git", "stage", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "files staged" in result.output
        finally:
            os.chdir(original)


class TestGitMerge:
    def test_conflict_always_exits_2(self, git_repo: Path) -> None:
        """Exit 2 even when git merge --abort also fails."""
        import os
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            with patch("subprocess.run") as mock_run:
                # merge fails with CONFLICT
                conflict_result = MagicMock()
                conflict_result.returncode = 1
                conflict_result.stdout = "CONFLICT (content): Merge conflict in file.txt"
                conflict_result.stderr = ""
                # abort also fails
                abort_result = MagicMock()
                abort_result.returncode = 1
                abort_result.stderr = "fatal: There is no merge to abort."
                mock_run.side_effect = [conflict_result, abort_result]
                result = runner.invoke(app, ["git", "merge", "some-branch"])
                assert result.exit_code == 2  # Always 2, even when abort fails
        finally:
            os.chdir(original)


class TestGitDelete:
    def test_not_merged_exits_2(self, git_repo: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            # Create an unmerged branch
            subprocess.run(["git", "checkout", "-b", "unmerged-branch"], cwd=git_repo, capture_output=True)
            (git_repo / ".specs" / "features" / "001-test" / "new.md").write_text("new")
            subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "unmerged"], cwd=git_repo, capture_output=True)
            subprocess.run(["git", "checkout", "-"], cwd=git_repo, capture_output=True)
            result = runner.invoke(app, ["git", "delete", "unmerged-branch"])
            assert result.exit_code == 2  # "not fully merged" → exit 2
        finally:
            os.chdir(original)


class TestGitStatus:
    def test_outputs_valid_json(self, git_repo: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(app, ["git", "status"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "branch" in data
            assert "staged" in data
            assert "ahead" in data
            assert "behind" in data
        finally:
            os.chdir(original)
```

- [ ] **Step 2:** Run tests → FAIL

- [ ] **Step 3:** Create `validator/git_ops.py` implementing the contract above

- [ ] **Step 4:** Add to `validator/cli.py`:

```python
from .git_ops import git_app
app.add_typer(git_app, name="git")
```

- [ ] **Step 5:** Run tests → PASS

---

### Task 12: Create validator/commit_context.py (TDD)

**Files:**
- Create: `validator/commit_context.py`
- Create: `tests/test_commit_context.py`
- Modify: `validator/cli.py` (temporary registration)

**ADR path discovery (do this before writing tests):**
- [ ] **Step 0:** Grep `system/templates/` and `system/spec-system.md` for "ADR" to confirm canonical path. Expected: `.specs/stacks/decisions/ADR-*.md`. Document the confirmed path as a comment in `commit_context.py` module docstring.

**Implementation contract:**
- `write`: `hooks_dir = specs_root / "hooks"; hooks_dir.mkdir(parents=True, exist_ok=True)` — never assume directory exists
- JSON schema v1: `{"version": 1, "feature_name": str, "spec_path": str, "plan_path": str, "adr_paths": str}` where `adr_paths` is comma-joined sorted absolute paths (empty string if no ADRs)

- [ ] **Step 1:** Create `tests/test_commit_context.py`:

```python
"""Tests for validator.commit_context — commit context bridge CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


@pytest.fixture()
def specs_root(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    feature_dir = specs / "features" / "001-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# spec")
    (feature_dir / "plan.md").write_text("# plan")
    return specs


class TestCommitContextWrite:
    def test_creates_file_schema_v1(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            context_path = specs_root / "hooks" / ".commit-context.json"
            assert context_path.exists()
            data = json.loads(context_path.read_text())
            assert data["version"] == 1
            assert "spec.md" in data["spec_path"]
            assert "plan.md" in data["plan_path"]
            assert isinstance(data["adr_paths"], str)
        finally:
            os.chdir(original)

    def test_overwrites_stale(self, specs_root: Path) -> None:
        import os
        (specs_root / "hooks").mkdir(exist_ok=True)
        (specs_root / "hooks" / ".commit-context.json").write_text('{"old": "data"}')
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads((specs_root / "hooks" / ".commit-context.json").read_text())
            assert "version" in data  # New schema, not old data
        finally:
            os.chdir(original)

    def test_creates_hooks_dir_when_missing(self, specs_root: Path) -> None:
        """write must succeed even when .specs/hooks/ doesn't exist yet."""
        import os
        assert not (specs_root / "hooks").exists()
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            assert (specs_root / "hooks" / ".commit-context.json").exists()
        finally:
            os.chdir(original)

    def test_adr_paths_empty_when_no_adrs(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads((specs_root / "hooks" / ".commit-context.json").read_text())
            assert data["adr_paths"] == ""
        finally:
            os.chdir(original)

    def test_adr_paths_populated_when_adrs_exist(self, specs_root: Path) -> None:
        import os
        adr_dir = specs_root / "stacks" / "decisions"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001-auth.md").write_text("# ADR-001")
        (adr_dir / "ADR-002-db.md").write_text("# ADR-002")
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads((specs_root / "hooks" / ".commit-context.json").read_text())
            assert "ADR-001-auth.md" in data["adr_paths"]
            assert "ADR-002-db.md" in data["adr_paths"]
        finally:
            os.chdir(original)


class TestCommitContextRead:
    def test_prints_json(self, specs_root: Path) -> None:
        import os
        (specs_root / "hooks").mkdir()
        ctx = {"version": 1, "feature_name": "001-test", "spec_path": "/x/spec.md", "plan_path": "/x/plan.md", "adr_paths": ""}
        (specs_root / "hooks" / ".commit-context.json").write_text(json.dumps(ctx))
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "read"], catch_exceptions=False)
            assert result.exit_code == 0
            assert json.loads(result.output)["feature_name"] == "001-test"
        finally:
            os.chdir(original)

    def test_exits_1_when_missing(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "read"])
            assert result.exit_code == 1
        finally:
            os.chdir(original)


class TestCommitContextClear:
    def test_removes_file(self, specs_root: Path) -> None:
        import os
        (specs_root / "hooks").mkdir()
        ctx_path = specs_root / "hooks" / ".commit-context.json"
        ctx_path.write_text('{"version": 1}')
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "clear"], catch_exceptions=False)
            assert result.exit_code == 0
            assert not ctx_path.exists()
        finally:
            os.chdir(original)

    def test_idempotent(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "clear"], catch_exceptions=False)
            assert result.exit_code == 0  # No error when file is already absent
        finally:
            os.chdir(original)
```

- [ ] **Step 2:** Run tests → FAIL

- [ ] **Step 3:** Create `validator/commit_context.py` with the implementation contract above

- [ ] **Step 4:** Add to `validator/cli.py`:

```python
from .commit_context import commit_context_app
app.add_typer(commit_context_app, name="commit-context")
```

- [ ] **Step 5:** Run tests → PASS

---

### Task 13: Finalize validator/cli.py — Register All Three

**Files:**
- Modify: `validator/cli.py`

- [ ] **Step 1:** Re-read `validator/cli.py` (full file — has been modified across Tasks 9-12)

- [ ] **Step 2:** Consolidate all `add_typer()` calls into final form:

```python
from .pipeline import pipeline_app
from .git_ops import git_app
from .commit_context import commit_context_app

app.add_typer(pipeline_app, name="pipeline")
app.add_typer(git_app, name="git")
app.add_typer(commit_context_app, name="commit-context")
```

Remove any duplicate or temporary partial registrations.

- [ ] **Step 3:** Run all tests (new + existing):

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/ -x -q --ignore=tests/integration
```

Expected: all pass.

- [ ] **Step 4:** `livespec --help` lists `pipeline`, `git`, `commit-context`

---

### Task 14: Update commands/feature.md — Branch 2 Changes

**Files:**
- Modify: `commands/feature.md`

- [ ] **Step 1:** Re-read `commands/feature.md` (full file — context may be stale from Branch 1 edits)

- [ ] **Step 2:** Grep for `pipeline.md` → enumerate all occurrences with line numbers → build replacement checklist. Expected: 15+ occurrences.

- [ ] **Step 3:** For each occurrence, classify:
  - **Write** (creates or updates pipeline.md) → replace with `livespec pipeline init` or `livespec pipeline update --phase <phase> --status <status> [--timestamp]`
  - **Read/resume** (reads state) → replace with `livespec pipeline read` or `livespec pipeline next`

- [ ] **Step 4:** Apply replacements in batches of max 3 edits, re-reading between batches

- [ ] **Step 5:** Replace staging instructions with:

```
Run: livespec git stage --feature {{feature_name}}
   (Stages all feature files + modified roadmap.md and changelog.md)

Run: livespec commit-context write --feature {{feature_name}}
   (Writes .specs/hooks/.commit-context.json with resolved spec/plan/ADR paths)

Run: livespec commit-context read
   (Read JSON output — use spec_path, plan_path, adr_paths in hook invocation step 6)
```

- [ ] **Step 6:** After `/git.commit` completes successfully, add:

```
Run: livespec commit-context clear
   (Removes .specs/hooks/.commit-context.json)
```

- [ ] **Step 7:** Re-read the full auto-commit and state tracking sections. Count remaining raw `pipeline.md` write references: **must be zero**

---

### Task 15: Update commands/ship.md

**Files:**
- Modify: `commands/ship.md`

- [ ] **Step 1:** Read `commands/ship.md` lines 190–260

- [ ] **Step 2:** Replace:

| Old | New |
|---|---|
| `git checkout -b feature/NNN-name` | `livespec git branch feature/NNN-name` |
| `git checkout <target>` + `git merge feature/NNN-name --no-ff` | `livespec git merge feature/NNN-name --no-ff` |
| `git branch -d feature/NNN-name` | `livespec git delete feature/NNN-name` |

- [ ] **Step 3:** After merge instruction, add:

```
On exit 2 (merge conflict):
  → Update ship.md: feature status → "Blocked (merge conflict)"
  → STOP. Display: "Merge conflict on feature/NNN-name. Fix manually, then /spec.ship --resume"

On livespec git delete exit 2 (not fully merged):
  → Display error and stop — use livespec git delete --force only after confirming the branch was actually merged
```

- [ ] **Step 4:** Re-read edited section

---

### Task 16: Update system/hooks.md and .gitignore

**Files:**
- Modify: `system/hooks.md`
- Modify: `.gitignore`

- [ ] **Step 1:** Re-read the `## Commit Hook` section in `system/hooks.md` (added in Task 2)

- [ ] **Step 2:** After the Gitignore paragraph, add:

```markdown
`.specs/hooks/.commit-context.json` is auto-generated at commit time by `livespec commit-context write` and must be gitignored. Add to `.gitignore`:

```
.specs/hooks/.commit-context.json
```
```

- [ ] **Step 3:** Read `.gitignore`; append `.specs/hooks/.commit-context.json`

- [ ] **Step 4:** Re-read `.gitignore` to verify

---

### Task 17: Integration Test in test-audit-fix

**Files:** test-audit-fix project only (no livespec changes)

- [ ] **Step 1:** Ensure livespec is installed:

```bash
pip install -e /Users/julienm/projects/livespec --quiet
```

- [ ] **Step 2:** Initialize LiveSpec in test-audit-fix if not already done:

```bash
bash /Users/julienm/projects/livespec/scripts/init.sh /Users/julienm/projects/test-audit-fix
```

- [ ] **Step 3:** Test `livespec pipeline` commands:

```bash
cd /Users/julienm/projects/test-audit-fix
livespec pipeline init --feature 001-test-feature
# Expected: pipeline.md created

livespec pipeline update --feature 001-test-feature --phase specify --status in_progress
# Expected: "Updated Specify → In Progress"

livespec pipeline read --feature 001-test-feature
# Expected: JSON with "specify": "In Progress"

livespec pipeline next --feature 001-test-feature
# Expected: "spec-review" (first non-done phase)
```

- [ ] **Step 4:** Mark all phases Done → verify exit 2:

```bash
for phase in specify spec-review plan plan-review preflight implement test; do
  livespec pipeline update --feature 001-test-feature --phase $phase --status done --timestamp
done
livespec pipeline next --feature 001-test-feature; echo "Exit code: $?"
# Expected: exit code 2 (all done = pipeline complete, NOT error)
```

- [ ] **Step 5:** Test `livespec git` commands:

```bash
cd /Users/julienm/projects/test-audit-fix
livespec git status
# Expected: valid JSON {branch, staged, ahead, behind}

livespec git branch feature/test-livespec-git
# Expected: "Created and checked out branch: feature/test-livespec-git"

livespec git status
# Expected: JSON showing "branch": "feature/test-livespec-git"

git checkout main 2>/dev/null || git checkout master
livespec git delete feature/test-livespec-git
# Expected: "Deleted branch: feature/test-livespec-git"
```

- [ ] **Step 6:** Test `livespec commit-context` commands:

```bash
cd /Users/julienm/projects/test-audit-fix
# Create minimal spec and plan files
mkdir -p .specs/features/001-test-feature
echo "# spec" > .specs/features/001-test-feature/spec.md
echo "# plan" > .specs/features/001-test-feature/plan.md

livespec commit-context write --feature 001-test-feature
# Expected: "Context written", .specs/hooks/ created if missing

livespec commit-context read
# Expected: JSON with spec_path, plan_path, adr_paths (empty), feature_name

livespec commit-context clear
# Expected: "Context cleared"

livespec commit-context clear
# Expected: exit 0 (idempotent)
```

---

### Task 18: Commit Branch 2

- [ ] **Step 1:** Run full test suite one final time:

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/ -x -q --ignore=tests/integration
```

Expected: all pass.

- [ ] **Step 2:** Stage all Branch 2 files:

```bash
cd /Users/julienm/projects/livespec
git add \
  validator/specs_utils.py \
  validator/pipeline.py \
  validator/git_ops.py \
  validator/commit_context.py \
  validator/cli.py \
  tests/test_pipeline.py \
  tests/test_git_ops.py \
  tests/test_commit_context.py \
  commands/feature.md \
  commands/ship.md \
  system/hooks.md \
  .gitignore
```

- [ ] **Step 3:** Invoke `/git.commit` with message: `feat(pipeline): add Python pipeline/git/commit-context CLI modules and update command orchestration`

---

## Self-Review: Spec Coverage Check

| Spec requirement | Task covering it |
|---|---|
| commit hook type `commit.md` (3-level resolution) | Task 2 |
| Template variables `{{spec_path}}`, `{{plan_path}}`, `{{adr_paths}}` | Task 3 |
| Fallback to `/git.commit` without `--intent` | Task 3 |
| Structural validation gate after spec.md | Task 4 |
| Structural validation gate after plan.md | Task 5 |
| Branch 2 forks from Branch 1 (no merge conflicts) | Task 8 |
| `find_specs_root` single source of truth | Task 9 |
| `livespec pipeline init/update/read/next` | Task 10 |
| `pipeline update` handles AI-generated whitespace padding | Task 10 |
| `pipeline next` exit 2 = all done (not error) | Task 10 |
| `livespec git branch/stage/merge/delete/status` | Task 11 |
| `merge` exit 2 even when abort fails | Task 11 |
| `delete` exit 2 for "not fully merged" | Task 11 |
| `livespec commit-context write/read/clear` | Task 12 |
| `write` creates `.specs/hooks/` if missing | Task 12 |
| `.commit-context.json` schema v1 | Task 12 |
| All 15+ pipeline.md writes replaced in feature.md | Task 14 |
| Git ops in ship.md use `livespec git` | Task 15 |
| `.commit-context.json` gitignored | Task 16 |
| Integration tests in test-audit-fix | Tasks 6, 17 |
| Unit tests for all 3 new Python modules | Tasks 10, 11, 12 |

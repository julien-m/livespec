#!/usr/bin/env python3
"""One-shot migration: append Section 13 to every commands/*.expectations.md.

Run from repo root:

    python3 scripts/migrate_expectations_section13.py

The script is idempotent: it skips files that already have a `## 13.` heading.
Intentionally not committed to LiveSpec runtime — it's a feature 040 migration.
"""

from __future__ import annotations

import re
from pathlib import Path

# The migration script embeds operator-facing Markdown fixtures verbatim so the
# generated expectations files preserve the reviewed wording and typography.
# ruff: noqa: E501, RUF001

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / "commands"


def section13_for(command: str) -> str:
    """Return a Section 13 Markdown block tailored to ``command``.

    The mapping below carries hand-crafted demo content for the three AC-011
    priority commands (init, test, feature) and concrete content for every
    other command.  All blocks satisfy the >= 3 content-line rule per
    sub-section.
    """
    blocks = {
        "init": _init_block,
        "test": _test_block,
        "feature": _feature_block,
        "specify": _specify_block,
        "plan": _plan_block,
        "implement": _implement_block,
        "check": _check_block,
        "fix": _fix_block,
        "explain": _explain_block,
        "stack": _stack_block,
        "ship": _ship_block,
        "preflight": _preflight_block,
        "hooks": _hooks_block,
        "play-coverage": _play_coverage_block,
        "refine": _refine_block,
        "status": _status_block,
        "refresh-conventions": _refresh_conventions_block,
        "migrate": _migrate_block,
        "propose": _propose_block,
        "verify-output": _verify_output_block,
    }
    return blocks[command]()


# ---- Per-command Section 13 blocks ----


def _init_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-init
> Phase 1 — Project discovery: detecting language, framework, tests
> Phase 2 — Stack proposal: <stack> (confidence: high)
> Phase 3 — Brainstorm: 4 user-story candidates, 1 ADR draft
> Wrote .specs/project.md, stacks/_default.md, roadmap.md, preflight.md
exit 0
```

### Files Produced

```
.specs/
├── README.md                    # spec registry index
├── spec-system.md               # universal rules (this project)
├── constitution.md              # architecture principles
├── project.md                   # vision, users, constraints
├── roadmap.md                   # MVP / Post-MVP / Future
├── stacks/_default.md           # chosen stack + rationale
├── stacks/decisions/ADR-001-*.md
├── testing/strategy.md
├── preflight.md                 # preflight manifest
└── preflight-report.md          # first run report
```

### Aligned / Drift / Missing

- **Aligned:** `.specs/` exists, project.md has real values, ADR-001 + stack rationale present, preflight-report.md verdict READY. Exit 0.
- **Drift:** project.md still contains `[TBD]` placeholders, stack rationale empty, or no ADR generated despite stack choice. Exit 1 with a gap report.
- **Missing:** Tooling preconditions failed (no git, no Python). Exit 2 with the missing tool name.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Fresh repo (small) | 60–180s | brainstorm rounds |
| Existing codebase reverse-engineer | 180–600s | code scan size |
| Large monorepo | 300–900s | feature inference |

### Edge Cases

- Repo already contains a stale `.specs/` from a previous version: `/spec-migrate` is suggested before re-running init.
- No git remote configured: init proceeds, leaves a warning in `preflight-report.md`.
- LLM rate-limited mid-brainstorm: init resumes from the last saved checkpoint on next invocation.

### Post-run Actions

- **On success:** review `project.md`, then run `/spec-propose` to pick the first feature.
- **On drift:** open `.specs/checks/<today>.md`, fix the flagged blanks, re-run init.
- **On blocked:** install the missing tool from `preflight-report.md`, re-run init.
"""


def _test_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-test <feature> --visual
> Auditing AC coverage: <feature> has 12 ACs, 9 covered, 3 missing
> Generating 3 missing scaffolds in apps/web/tests/e2e/<feature>/
> Running 38 specs across 1 surface (web)
> Visual: 13 baselines · 0 diff · 1 missing (<screen>)
> AC coverage: 12/12 ✓  Visual: 12/13 ✗ (1 missing)
exit 1
```

### Files Produced

```
apps/web/tests/e2e/<feature>/
├── happy-path.spec.ts          # generated from AC-001..AC-003
├── edge-cases.spec.ts          # generated from EC-001..EC-005
└── visual.spec.ts              # screenshot grid
.specs/features/<feature>/
├── baselines/
│   └── <screen>.png             # captured (if --update)
└── checks/<date>-test.md        # AC coverage report
```

### Aligned / Drift / Missing

- **Aligned:** All AC scaffolded, all tests pass, visual diff 0 across all screens. Exit 0 with `Visual: N baselines · 0 diff`.
- **Drift:** Some AC have no test (gap), or pixel diff exceeds threshold on a screen. Exit 1 with a per-AC and per-screen report.
- **Missing:** No `<surface>` testDir configured, or no Playwright config detected. Exit 2 naming the surface and the recovery command.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single surface, cached browsers | 20–60s | spec count |
| Visual + screenshot capture | 60–180s | screen count |
| Multi-surface (web + native) | 120–600s | converge cost |

### Edge Cases

- New screen mentioned in `spec.md` but missing PNG mockup: report flags `[no mockup]` and falls back to a layout-only baseline.
- Driver in `--migrate` mode: tests are regenerated under the new naming convention; old `.skip` versions are kept until `--commit`.
- `--regenerate-missing` invoked: only baselines absent on disk are captured; pre-existing baselines are NEVER overwritten without `--update`.

### Post-run Actions

- **On success:** commit baselines + checks file, push.
- **On drift:** open the gap report, fix code or update spec; re-run with `--update` when ready to re-baseline.
- **On blocked:** create the surface entry in `.specs/surfaces.yaml`, then re-run.
"""


def _feature_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-feature -a "Add CSV export"
> Phase 1 (Specify): spawning agent — 1 spec.md drafted (12 FR, 9 AC)
> Gate 1: review PASS — proceeding
> Phase 2 (Plan): spawning agent — 1 plan.md drafted (8 steps)
> Gate 2: review PASS — proceeding
> Phase 2.7 (Preflight): READY
> Phase 3 (Implement): 8/8 steps done — 14 files changed, 27 tests pass
> Phase 3.5 (Test): AC coverage 9/9 — visual: skipped
> Auto-commit: 1 commit pushed on feature/<feature>
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── spec.md                    # 12 FR, 9 AC, 4 user stories
├── plan.md                    # technical plan, sequence diagrams
├── pipeline.md                # phase tracker (Done × 7)
├── progress.md                # step-by-step checkpoint
├── implementation.md          # FR → file map
└── changelog.md               # first entry
```

### Aligned / Drift / Missing

- **Aligned:** all 5 phases Done, AC coverage 100%, no review findings remain, one commit on the feature branch. Exit 0.
- **Drift:** Phase 1.5 or 2.5 returns BLOCKING findings; in `--auto` mode pipeline retries up to 2× then aborts. Exit 1.
- **Missing:** Preflight failed critical check (no git, no Python, no LLM creds). Exit 2 with the failing check name.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small feature (S, no UI) | 5–10 min | story count |
| Medium feature (M, 1 surface) | 10–25 min | tests + AC count |
| Large feature (L, multi-surface) | 25–60 min | implementation surface |

### Edge Cases

- `--resume`: reads `pipeline.md` and re-spawns the first non-Done phase agent; never re-runs Done phases.
- `--mono`: implement phase runs single-agent (no Superpowers dispatch); feature-level supervisor still spawns Specify/Plan/Implement/Test separately.
- `--economy`: disables ALL sub-agent dispatch; all phases run inline. Lossless, just slower.

### Post-run Actions

- **On success:** open the commit, push, request review.
- **On drift:** read `FINDINGS_DETAIL` in `pipeline.md`, fix the spec/plan, re-run with `--resume`.
- **On blocked:** run `/spec-preflight` standalone to identify the missing prerequisite.
"""


def _specify_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-specify "Add filter chips to search results"
> Detected scope: M · Stories: 3 (P1 × 2, P2 × 1)
> Drafting spec.md (9 AC, 11 FR)
> Wrote .specs/features/<feature>/spec.md
> Updated .specs/roadmap.md (checked the matching item)
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── spec.md                # user stories + AC + FR + Mermaid flowcharts
└── changelog.md           # first entry "spec: add <feature>"
.specs/roadmap.md          # roadmap item checked
.specs/changelog.md        # summary line appended
```

### Aligned / Drift / Missing

- **Aligned:** spec.md exists with Gherkin + Mermaid for every story, ACs numbered, FRs mapped. Exit 0.
- **Drift:** spec contains `[NEEDS CLARIFICATION]` markers > 3, or a story lacks Gherkin. Exit 1 with the gap report.
- **Missing:** `.specs/project.md` not found. Exit 2 with recovery `Run /spec-init first`.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small spec (1 story) | 30–60s | LLM latency |
| Medium spec (3 stories) | 60–180s | story expansion |
| Large spec (5+ stories + ER) | 180–300s | diagram generation |

### Edge Cases

- Description references a feature that overlaps an existing one: spec.specify proposes a split and writes a `seed.md` for each sub-feature.
- LLM emits Mermaid syntax errors: spec.specify retries once, then fails with the malformed block highlighted.
- Roadmap already has a matching item: it gets checked and linked to the new feature folder.

### Post-run Actions

- **On success:** run `/spec-plan <feature>` next.
- **On drift:** open spec.md, resolve `[NEEDS CLARIFICATION]`, re-run with `--refine`.
- **On blocked:** run `/spec-init`, then retry.
"""


def _plan_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-plan <feature>
> Loaded spec.md (9 AC, 11 FR)
> Drafting plan.md — 8 steps, 1 sequence diagram, 1 state diagram
> Constitution check: PASS
> Wrote .specs/features/<feature>/plan.md
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── plan.md                # file-by-file plan, diagrams, testing strategy
└── changelog.md           # entry "plan: draft <feature>"
```

### Aligned / Drift / Missing

- **Aligned:** plan.md has Technical Context, Constitution Check, sequence/state/ER diagrams as appropriate, and one step per FR. Exit 0.
- **Drift:** Constitution Check missing or an FR is uncovered in the plan. Exit 1.
- **Missing:** spec.md not found for the feature. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small plan (3 steps) | 30–60s | LLM call count |
| Medium plan (8 steps) | 60–180s | diagram drafting |
| Plan with ER + state diagrams | 120–300s | entity count |

### Edge Cases

- Plan references libraries not in the stack: spec.plan warns and suggests adding an ADR.
- `--no-contracts`: skips OpenAPI/GraphQL emission; useful when the feature exposes no API.
- Plan exceeds 800 lines: spec.plan suggests splitting the feature.

### Post-run Actions

- **On success:** review plan.md, then run `/spec-implement <feature>`.
- **On drift:** open the gap report, refine plan.md, re-run `--refine`.
- **On blocked:** run `/spec-specify` first.
"""


def _implement_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-implement <feature>
> Loaded plan.md — 8 steps queued
> Step 1/8: src/api/csv-export.ts (create) — 42 lines
> Step 2/8: tests/api/csv-export.test.ts — 6 tests PASS
> ... (steps 3-7 elided)
> Step 8/8: docs/exports.md (update) — 12 lines
> All steps Done · 27 tests pass · implementation.md generated
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── progress.md            # step-by-step checkpoint (MANDATORY)
├── implementation.md      # FR/AC → file map with @spec anchors
├── logs/<date>.md         # execution log (unless --no-save)
└── changelog.md           # entry "impl: <feature>"
src/<...> + tests/<...>    # code under each step
```

### Aligned / Drift / Missing

- **Aligned:** every step in progress.md is Done, implementation.md maps all FR/AC to anchors, all tests pass. Exit 0.
- **Drift:** one step failed and was rolled back; progress.md shows it `Blocked` with reason. Exit 1.
- **Missing:** plan.md not found, or preflight check failed. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small (3 steps) | 2–5 min | step latency |
| Medium (8 steps) | 5–20 min | test compile time |
| Large (15+ steps) | 20–60 min | step orchestration |

### Edge Cases

- `--resume`: reads progress.md and continues at the first non-Done step.
- `--step`: pauses between steps for manual validation.
- A step's tests fail twice: implement stops, marks the step Blocked, surfaces the failing output.

### Post-run Actions

- **On success:** run `/spec-test <feature>` to lock visual baselines.
- **On drift:** inspect progress.md, fix the failing step, re-run with `--resume`.
- **On blocked:** run `/spec-plan` first, or unblock the preflight check.
"""


def _check_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-check <feature>
> Scanning code for @spec anchors → 27 matches
> Cross-referencing with spec.md FR/AC → 2 unmapped FRs
> Visual fidelity: 12/13 screens match (1 drift: <screen>)
> Wrote .specs/features/<feature>/checks/<date>.md
exit 1
```

### Files Produced

```
.specs/features/<feature>/checks/<date>.md   # gap report
```

### Aligned / Drift / Missing

- **Aligned:** every FR/AC has at least one `@spec` anchor in code; visual diff < threshold for every screen. Exit 0.
- **Drift:** unmapped FR/AC, missing test, or visual drift > threshold. Exit 1, gap report names each issue.
- **Missing:** spec.md absent or `@spec` anchor convention not configured. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Code-only check | 10–30s | ripgrep span |
| Code + visual | 30–120s | screenshot count |
| Code + visual + surfaces | 60–300s | surface count |

### Edge Cases

- Code has a `@spec` anchor pointing to a deleted FR: check reports `orphan anchor`.
- Visual driver disabled: only structural check runs.
- `--surfaces` flag: detects drift between `.specs/surfaces.yaml` and the actual filesystem.

### Post-run Actions

- **On success:** done.
- **On drift:** run `/spec-fix <feature>` for visual drift, or edit code/spec for structural drift.
- **On blocked:** run `/spec-specify` first.
"""


def _fix_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-fix <feature>
> Reading checks/<date>.md → 3 issues
> Issue 1/3: visual drift on <screen> → re-rendering component
> Issue 2/3: missing @spec anchor on src/api/foo.ts:45
> Issue 3/3: unmapped FR-008 → added stub test
> All issues addressed — re-run /spec-check to verify
exit 0
```

### Files Produced

```
src/<modified files>
tests/<new or modified tests>
.specs/features/<feature>/implementation.md   # anchors refreshed
```

### Aligned / Drift / Missing

- **Aligned:** every issue from the gap report has a corresponding patch; re-running /spec-check returns 0. Exit 0.
- **Drift:** some issues could not be auto-fixed; the report lists them as `manual`. Exit 1.
- **Missing:** no gap report under `.specs/features/<feature>/checks/`. Exit 2 with recovery `/spec-check first`.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Few small issues | 30–90s | LLM call count |
| Visual drift (multi-screen) | 60–300s | re-render cost |
| Many structural issues | 120–600s | per-issue patch loop |

### Edge Cases

- `--dry-run`: shows the patch plan without writing files.
- Visual fix needs a design mockup change: fix flags it as `manual — update design source`.
- Auto-fix produces a regression in another test: fix rolls back and surfaces the conflict.

### Post-run Actions

- **On success:** re-run `/spec-check <feature>` to confirm zero gaps.
- **On drift:** address the `manual` issues by hand, re-run `/spec-fix`.
- **On blocked:** run `/spec-check <feature>` to generate the gap report.
"""


def _explain_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-explain <feature>
> Loading spec.md, plan.md, implementation.md, changelog.md
> Synthesizing living documentation for <feature>
> Section: Overview · User flows · Architecture · Files · History
exit 0
```

### Files Produced

```
(stdout only — Markdown narrative)
```

### Aligned / Drift / Missing

- **Aligned:** Markdown explanation covers Overview, User flows, Architecture, Files, History sections. Exit 0.
- **Drift:** the feature has partial implementation; explanation marks missing FR/AC explicitly. Exit 0 still (read-only command).
- **Missing:** feature directory not found. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small feature | 15–45s | doc length |
| Medium feature | 45–120s | story count |
| Large feature | 120–300s | implementation breadth |

### Edge Cases

- Implementation lacks @spec anchors: explanation falls back to file inference.
- Multiple changelog entries: explanation summarizes them as a timeline.
- `--json`: emits structured envelope instead of prose.

### Post-run Actions

- **On success:** share the output with reviewers; pipe to a doc site if desired.
- **On drift:** no action.
- **On blocked:** confirm the feature slug; run `/spec-status` to list features.
"""


def _stack_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-stack
> Current stack: <stack>
> Impact analysis: 3 files affected by your draft change
> Drafting ADR-012-replace-pg-with-sqlite.md
> Wrote .specs/stacks/decisions/ADR-012-*.md
exit 0
```

### Files Produced

```
.specs/stacks/decisions/ADR-NNN-*.md      # new ADR
.specs/stacks/_default.md                  # updated if stack identity changed
.specs/changelog.md                        # stack: ADR-NNN entry
```

### Aligned / Drift / Missing

- **Aligned:** ADR exists with Context, Decision, Consequences sections, stack rationale updated. Exit 0.
- **Drift:** ADR missing one of the canonical sections. Exit 1.
- **Missing:** `.specs/stacks/` directory not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single ADR | 20–60s | LLM call |
| ADR + impact analysis | 60–180s | repo scan |
| ADR + propagation to features | 180–600s | feature touch count |

### Edge Cases

- Stack change affects existing features: spec.stack lists them and proposes `/spec-refine` to update each.
- `--view`: read-only mode lists the current stack and ADRs without prompting changes.
- ADR conflicts with a previous one: spec.stack surfaces the conflict for manual resolution.

### Post-run Actions

- **On success:** run `/spec-refresh-conventions` if the stack identity changed.
- **On drift:** edit the ADR to add missing sections.
- **On blocked:** run `/spec-init` first.
"""


def _ship_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-ship
> Scanning roadmap.md — 3 unchecked items in MVP tier
> Picking next: <feature>
> Spawning /spec-feature -a "<feature>" --branch
> Pipeline complete → SHIP_RESULT: OK on feature/<feature>
> Continuing batch: 2 remaining
exit 0
```

### Files Produced

```
.specs/features/<feature>/             # one folder per shipped feature
git branches:                          # feature/<feature> × N
```

### Aligned / Drift / Missing

- **Aligned:** every targeted roadmap item is shipped (commit + PR), SHIP_RESULT: OK for each. Exit 0.
- **Drift:** one feature returned SHIP_RESULT: BLOCKED; batch halts. Exit 1 with the failing feature name.
- **Missing:** roadmap.md absent or empty. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single feature | 5–25 min | feature size |
| Batch of 3 small features | 15–60 min | sum of per-feature time |
| Full MVP tier | 60–240 min | feature count × scope |

### Edge Cases

- `--limit N`: ships at most N features then stops.
- `--dry-run`: prints the batch plan without spawning any pipeline.
- A feature fails mid-batch: ship logs the failure and offers `--resume` to skip past.

### Post-run Actions

- **On success:** review the resulting PRs.
- **On drift:** open the failing feature's pipeline.md, fix the blocker, re-run with `--resume`.
- **On blocked:** populate roadmap.md via `/spec-propose`.
"""


def _preflight_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-preflight
> Running 7 checks from .specs/preflight.md
> ✓ git ≥ 2.30
> ✓ python3 ≥ 3.11
> ✓ playwright installed (1.45)
> ⚠ ANTHROPIC_API_KEY missing (warning, not critical)
> Wrote .specs/preflight-report.md — verdict: WARNINGS
exit 0
```

### Files Produced

```
.specs/preflight-report.md     # verdict (READY | WARNINGS | BLOCKED), per-check status
```

### Aligned / Drift / Missing

- **Aligned:** every critical check passes, report verdict READY. Exit 0.
- **Drift:** only warnings; verdict WARNINGS. Exit 0 (non-blocking by design).
- **Missing:** a critical check fails. Exit 2 with the failing check and recovery command.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Pure tooling check | 2–10s | binary lookup |
| Tooling + LLM creds | 5–20s | network |
| Full stack + autofix | 10–60s | autofix loop |

### Edge Cases

- `--light`: runs only critical checks (used by /spec-feature 2.7).
- `--autofix`: attempts to install missing deps when safe.
- Check command crashes: preflight reports `error` for that line, continues.

### Post-run Actions

- **On success:** proceed with `/spec-feature` or the targeted command.
- **On drift:** address the warnings if relevant; no blocker.
- **On blocked:** run the recovery command from the report, re-run preflight.
"""


def _hooks_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-hooks plan
> Resolved hooks for "plan":
> [global] ~/.claude/livespec/hooks/before-plan.md
> [project] .specs/hooks/before-plan.md
> Mode: extend (chain executes both)
exit 0
```

### Files Produced

```
(read-only — prints hook chain to stdout)
```

### Aligned / Drift / Missing

- **Aligned:** hook chain is printed with file paths and mode. Exit 0.
- **Drift:** local hook declares `mode: override` but the same level lacks content. Exit 1 (validation).
- **Missing:** the command name doesn't exist. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single command resolution | 1–3s | filesystem only |
| `--create` | 3–10s | template scaffold |
| `--edit` | depends on editor | user time |

### Edge Cases

- `--create` on a level that already exists: hooks prompts before overwriting.
- `mode: override` at local level: chain shortens to one entry; spec.hooks marks the chain explicitly.
- Hook file is invalid YAML frontmatter: spec.hooks reports the parse error.

### Post-run Actions

- **On success:** review the chain; if customization is needed, run `--create local`.
- **On drift:** fix the offending hook's frontmatter.
- **On blocked:** verify the command spelling.
"""


def _play_coverage_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-play-coverage
> Building grep index for .specs/ ↔ src/
> 47 spec anchors found · 4 unmapped FRs
> Listening on http://localhost:4810 (Ctrl-C to stop)
```

### Files Produced

```
.specs/.coverage-cache.json     # transient grep cache (gitignored)
```

### Aligned / Drift / Missing

- **Aligned:** server starts, browser shows coverage matrix with green/red cells. Exit 0 on graceful stop.
- **Drift:** unmapped FR count > 0; the UI highlights them red. Exit 0 still (informational).
- **Missing:** port already in use. Exit 2 with `--port <N>` recovery suggestion.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small repo | 1–5s startup | ripgrep size |
| Medium repo | 5–15s startup | anchor count |
| Large monorepo | 15–60s startup | file traversal |

### Edge Cases

- No spec anchors found in code: the UI displays a single placeholder row.
- `--once`: emit a JSON snapshot to stdout and exit 0 without starting the server.
- Browser cannot reach the server (corporate proxy): use `--host 0.0.0.0` and the local IP.

### Post-run Actions

- **On success:** Ctrl-C when done.
- **On drift:** add @spec anchors to source files for the highlighted FRs.
- **On blocked:** retry on a different `--port`.
"""


def _refine_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-refine <feature>
> Loaded spec.md and plan.md for <feature>
> Conversational refinement: 3 questions
> Wrote refinements to spec.md (+12 lines, -3 lines)
> Updated changelog.md
exit 0
```

### Files Produced

```
.specs/features/<feature>/spec.md       # refined
.specs/features/<feature>/plan.md       # refined if --plan
.specs/features/<feature>/changelog.md  # new entry
```

### Aligned / Drift / Missing

- **Aligned:** spec/plan updated with traceable changelog entry, no schema regression. Exit 0.
- **Drift:** refinement introduces `[NEEDS CLARIFICATION]` markers > previous count. Exit 1.
- **Missing:** target spec/plan absent. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small refine | 30–90s | conversation turns |
| Project-level refine | 60–240s | profile re-evaluation |
| Plan refine with diagrams | 90–300s | re-rendering |

### Edge Cases

- `project` subject: re-evaluates roadmap after profile changes.
- `plan` subject: targets only plan.md.
- Refinement removes an AC: refine confirms the removal interactively and adjusts FR mapping.

### Post-run Actions

- **On success:** run `/spec-check <feature>` to confirm code alignment.
- **On drift:** open spec.md and resolve `[NEEDS CLARIFICATION]`.
- **On blocked:** confirm the feature slug.
"""


def _status_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-status
> Roadmap: 3 MVP · 5 Post-MVP · 2 Future · 1 Deferred
> Features in progress: 2 (<feature>, <feature>)
> Last activity: 2026-05-12 14:22 — impl: 040
exit 0
```

### Files Produced

```
(read-only — prints summary to stdout)
```

### Aligned / Drift / Missing

- **Aligned:** summary lists tier counts, in-progress features, recent changelog. Exit 0.
- **Drift:** spec.status detects a feature without a pipeline.md and flags it as orphan. Exit 0 (informational).
- **Missing:** `.specs/` not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small project | < 2s | file count |
| Large project | 2–10s | feature folder count |
| Project with logs | 5–20s | log aggregation |

### Edge Cases

- `--json`: emits a structured envelope for machine consumption.
- Multiple features with overlapping branches: status lists them all with branch markers.
- Roadmap has Deferred items: they appear in their own line, distinct from Future.

### Post-run Actions

- **On success:** decide which feature to advance next.
- **On drift:** investigate the flagged orphan feature.
- **On blocked:** run `/spec-init`.
"""


def _refresh_conventions_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-refresh-conventions
> Reading .specs/stacks/_default.md (<stack>)
> Generating .conventions/manifest.yaml + index.md
> 4 sub-domains detected: code, design-tokens, design-components, design-views
exit 0
```

### Files Produced

```
.conventions/manifest.yaml    # machine-readable
.conventions/index.md         # routing table
```

### Aligned / Drift / Missing

- **Aligned:** manifest.yaml and index.md exist with matching sub-domains. Exit 0.
- **Drift:** manifest declares sub-domains the source files no longer define. Exit 1.
- **Missing:** ai-ressources path unresolved or stack file absent. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Minimal stack | 1–5s | sub-domain count |
| Full stack | 5–20s | source file count |
| With `--full` re-detect | 20–60s | exclusion analysis |

### Edge Cases

- `--full`: re-detects sub-domains from scratch (used after stack identity change).
- ai-ressources repo not cloned locally: refresh emits a clear error with the expected `$AIRESOURCES` path.
- Old compiled-format `.conventions/` detected: refresh prompts migration.

### Post-run Actions

- **On success:** subsequent commands auto-load the new conventions.
- **On drift:** run `--full` to rebuild from scratch.
- **On blocked:** set `AIRESOURCES` env var, or run `/spec-init` first.
"""


def _migrate_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-migrate
> Current project version: v2 · LiveSpec repo version: v9
> Migrations to apply: 7 (v3 → v9)
> Applying v3: rename .specs/specs/ → .specs/features/
> ... (steps 2-6 elided)
> Applying v9: write .specs/surfaces.yaml
> All migrations applied successfully
exit 0
```

### Files Produced

```
.specs/livespec-version       # bumped to the latest version
.specs/<various artifacts>    # per migration
```

### Aligned / Drift / Missing

- **Aligned:** every migration applied, livespec-version matches repo VERSION, no manual fixups required. Exit 0.
- **Drift:** a migration encountered conflicting custom edits and skipped the file; report names it. Exit 1.
- **Missing:** `.specs/` not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| One migration | 1–5s | file count |
| Multiple structural | 5–30s | rename volume |
| Full v1 → v9 catch-up | 30–120s | feature count |

### Edge Cases

- `--dry-run`: print the migration plan without writing.
- A migration fails mid-way: spec.migrate rolls back the partial step, leaves a clean state.
- Custom hooks reference paths that the migration renamed: migrate updates the references.

### Post-run Actions

- **On success:** review the changelog entry, commit.
- **On drift:** open the skipped file, apply the migration manually.
- **On blocked:** run `/spec-init`.
"""


def _propose_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ /spec-propose
> Reading project.md, roadmap.md, recent changelog
> Top 3 suggestions:
>   1. Add CSV export · Scope: M · Roles: backend
>   2. Search by date range · Scope: S · Roles: frontend
>   3. Audit log viewer · Scope: M · Roles: full-stack
exit 0
```

### Files Produced

```
(read-only — prints suggestions; nothing written unless --append-roadmap)
```

### Aligned / Drift / Missing

- **Aligned:** ≥ 1 suggestion printed with name, scope, roles, deps. Exit 0.
- **Drift:** roadmap already exhausts the obvious features; suggestions become speculative. Exit 0 (informational).
- **Missing:** project.md absent. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small project | 10–30s | LLM call |
| Medium project | 30–90s | history scan |
| Large project | 60–180s | doc depth |

### Edge Cases

- `--append-roadmap`: writes the top-N suggestions to roadmap.md MVP tier.
- Roadmap already has a similar item: propose dedups and links to the existing line.
- LLM rate-limited: propose retries once, then exits 1 with the rate-limit hint.

### Post-run Actions

- **On success:** run `/spec-specify "<chosen suggestion>"`.
- **On drift:** ignore; propose is advisory.
- **On blocked:** run `/spec-init`.
"""


def _verify_output_block() -> str:
    return """## 13. Demo Session

### Live Console Output

```
$ livespec verify-output specify
verify-output  command=specify
source         commands/spec-specify.expectations.md
artifact       .specs/.runs/specify-2026-05-12T10-00-00.json

verb      kind                  status    detail
--------------------------------------------------------------------------------
must      exit_code             PASS      exit_code expected=0 actual=0
must      contains              PASS      substring 'spec.md created'
must_not  contains              PASS      substring 'Traceback'

outcome   success
exit_code 0
```

### Files Produced

```
(no filesystem writes in default mode; --save under --preview writes .specs/.previews/)
.specs/.previews/<name>-<timestamp>.md   # only when --preview --save
```

### Aligned / Drift / Missing

- **Aligned:** all `must` rules PASS, exit 0.
- **Drift:** at least one `must` rule FAILS but the run itself exited 0; outcome `drift`, exit 1.
- **Missing:** no run artifact, missing expectations file, or malformed override; outcome `blocked`, exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small artifact | < 1s | rule count |
| Visual when-branch active | 1–5s | filesystem walks |
| Preview mode | 1–3s | project scan |

### Edge Cases

- `--preview`: skips artifact resolution entirely; produces a Markdown report from Section 13 instantiated with project data.
- `--preview --save`: writes the rendered Markdown to `.specs/.previews/<command>-<ISO>.md`.
- `--json`: emits a JSON envelope (or `{command, project_root, timestamp, markdown}` under `--preview`).

### Post-run Actions

- **On success:** done; CI may archive the report.
- **On drift:** inspect the failing rule's `detail`, fix the command or the expectation.
- **On blocked:** run the command at least once (`livespec run wrap <cmd>` produces the artifact), or fix the override file.
"""


# ---- Generic patcher ----


def patch_file(path: Path) -> bool:
    """Append Section 13 to ``path`` unless already present.

    Returns True if the file was modified, False if it was a no-op.
    """
    text = path.read_text(encoding="utf-8")
    if re.search(r"^## 13\.", text, re.MULTILINE):
        return False
    command_name = path.name.removesuffix(".expectations.md")
    block = section13_for(command_name)
    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + block
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    updated = 0
    total = 0
    for path in sorted(COMMANDS_DIR.glob("*.expectations.md")):
        total += 1
        if patch_file(path):
            updated += 1
            print(f"updated {path.relative_to(REPO_ROOT)}")
        else:
            print(f"skipped (already has section 13): {path.relative_to(REPO_ROOT)}")
    print(f"--- {updated}/{total} files updated ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

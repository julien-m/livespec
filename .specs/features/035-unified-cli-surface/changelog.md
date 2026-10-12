## 2026-10-12 — [Test]: Help-example test strips ANSI styling

- **Type:** Test fix (PR #36 CI)
- **Spec modified:** No
- **Code modified:** `tests/test_cli_unified_exit_codes.py`
- **Cause:** under GitHub Actions Rich colors `--help`, so the AC-013 example line was parsed with ANSI escape codes as arguments.
- **Proof:** passes with `GITHUB_ACTIONS=true` on Python 3.12.
- **Author:** spec-fix (claude-code)

## 2026-10-12 — [Bugfix]: Fix: AC-013 help examples, constitution exit codes, base order, JSON summary channel, AC-002 feature selection

- **Type:** Bug Fix
- **Spec modified:** Yes (human decisions in Clarifications: exit-code taxonomy 0/1/2/3/130 with the shared `.specs/` resolver exception, base branch origin/HEAD then main, master, develop, dev, JSON summary on stderr, feature-scoped selection with `test_selection: append`; AC-002, AC-004, AC-011, AC-012, AC-013, FR-001, FR-005, FR-006, FR-007, FR-009, EC-004, EC-005 reworded; Mermaid added to Stories 3–5; Deps +033; status Draft → In Progress)
- **Plan modified:** Yes (rewritten: technical context, constitution check, sequence diagrams, steps 1–12)
- **Code modified:** `validator/cli_exit_codes.py`, `validator/cli_resolvers.py`, `validator/exceptions.py`, `validator/cli_commands/_common.py`, `test_cmd.py`, new `test_selection.py`, `coverage_cmd.py`, `drivers_cmd.py`, `mutation_cmd.py`, `preflight_cmd.py`, `validator/drivers/schemas.py`, `validator/drivers/runner.py`, `livespec/drivers/python.yaml`, driver template, `docs/cli-reference.md`, `.claude/commands/cli.md`, `.agent-sync/skills/source-command-cli/SKILL.md`
- **Tests:** new `tests/test_cli_unified_exit_codes.py`, `tests/test_cli_unified_feature.py`, `tests/test_cli_unified_acceptance.py`; `tests/test_cli_unified.py` expectations moved to the new codes
- **Gaps closed:** AC-013 (an `Example: livespec <command> …` epilog per command, parsed by the command's own parser), AC-002 (previously informational), AC-004, AC-011, AC-012; AC-003, AC-005, AC-008, AC-010 and AC-014 gained their first tests
- **Reviews:** independent spec and plan reviews, complete and ready; `--progression implement` READY
- **Remaining:** feature-scope conventions verify reports pre-existing debt (24 blocking findings), so the feature is not closed
- **Author:** spec-fix (Claude Opus 5.5)

## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog: 035-unified-cli-surface

## 2026-05-07 — Spec Update: Initial draft

- **Type:** Spec Update
- **Spec modified:** Yes (initial draft)
- **Code modified:** none
- **AC impacted:** AC-001 through AC-016
- **Author:** human (julien) via Claude Opus 4.7

## 2026-05-07 — Implementation: 5 unified CLI subcommands + docs + slash command

- **Type:** Feature Implementation
- **Spec modified:** No
- **Code modified:** Yes
- **AC impacted:** AC-001 through AC-016 (all)
- **Files added:**
  - `validator/cli_exit_codes.py` (FR-007)
  - `validator/cli_resolvers.py` (FR-006)
  - `validator/cli_commands/__init__.py`
  - `validator/cli_commands/_common.py`
  - `validator/cli_commands/test_cmd.py` (FR-001)
  - `validator/cli_commands/coverage_cmd.py` (FR-002)
  - `validator/cli_commands/drivers_cmd.py` (FR-003)
  - `validator/cli_commands/mutation_cmd.py` (FR-004)
  - `validator/cli_commands/preflight_cmd.py` (FR-005)
  - `tests/test_cli_unified.py` (FR-012, 26 tests)
  - `docs/cli-reference.md` (FR-010, AC-015)
  - `.claude/commands/cli.md` (FR-011, AC-016)
- **Files modified:**
  - `validator/cli.py` — registered the 5 unified subcommands
  - `validator/preflight_autofix.py` — added public `verify_item` wrapper
- **Tests:** 992 passed, 28 skipped (917 baseline + 26 new tests + 49 from concurrent merges)
- **Author:** Claude Opus 4.7 via `/spec.feature 035-unified-cli-surface --auto --branch`

## 2026-10-12 — [Refactor]: Help smoke test removed

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_cli_unified.py
- **AC impacted:** AC-013 (unmet product promise reported)
- **Author:** Claude Code (test-suite cleanup, lot 1)
- `test_each_command_has_help` only checked that Typer prints 'Usage'. AC-013 also promises one example per command; the shipped help of test/coverage/drivers/mutation/preflight contains no example, so the AC is not met by the product.

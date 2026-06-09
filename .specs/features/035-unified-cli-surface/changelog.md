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

---
title: "Unified CLI Surface — Plan"
status: "Approved"
created: 2026-05-07
updated: 2026-05-07
---

# Plan — Unified CLI Surface (Feature 035)

## Architecture

Add 5 new Typer subcommands (`test`, `coverage`, `drivers`, `mutation`, `preflight`) directly under the `livespec` root in `validator/cli.py`. Implementation logic lives in dedicated thin modules; auto-detection is centralized in `validator/cli_resolvers.py`; exit codes in `validator/cli_exit_codes.py`.

## Files to create

1. `validator/cli_exit_codes.py` — constants 0..5 (FR-007, AC-011)
2. `validator/cli_resolvers.py` — pure functions: `detect_specs_root`, `detect_base_branch`, `detect_current_feature`, `read_threshold_from_conventions` (FR-006)
3. `validator/cli_commands/__init__.py`
4. `validator/cli_commands/_common.py` — shared helpers: `summary_line()`, `print_error()`, `_pick_driver()`, etc.
5. `validator/cli_commands/test_cmd.py` — `livespec test` (FR-001)
6. `validator/cli_commands/coverage_cmd.py` — `livespec coverage` (FR-002)
7. `validator/cli_commands/drivers_cmd.py` — `livespec drivers` (FR-003)
8. `validator/cli_commands/mutation_cmd.py` — `livespec mutation` (FR-004)
9. `validator/cli_commands/preflight_cmd.py` — `livespec preflight` (FR-005)
10. `tests/test_cli_unified.py` — happy + edge per command (FR-012)
11. `docs/cli-reference.md` — exhaustive reference (FR-010, AC-015)
12. `.claude/commands/cli.md` — interactive slash command (FR-011, AC-016)

## Files to modify

- `validator/cli.py` — wire up the 5 new `@app.command()` callbacks (one-liners delegating to the modules)
- `.specs/features/035-unified-cli-surface/changelog.md` — record initial implementation

## Implementation steps

1. Exit codes constants module
2. Resolver functions (pure, fully unit tested)
3. `_common.py` shared logic (driver pick, error wrapper)
4. `drivers` subcommand (smallest, no subprocess)
5. `coverage` subcommand
6. `test` subcommand (uses run_capability)
7. `mutation` subcommand (uses run_mutation)
8. `preflight` subcommand (read-only + --fix delegates to preflight_autofix)
9. Tests
10. Documentation (`docs/cli-reference.md`, `.claude/commands/cli.md`)

## Exit codes (AC-011)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Missing `.specs/` or not a git repo |
| 2 | No driver match |
| 3 | Coverage threshold failed |
| 4 | Capability not supported by driver |
| 5 | Preflight critical failure |

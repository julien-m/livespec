---
created_at: '2026-05-12'
current_state: Done
feature_slug: 039-command-expectations-and-verify-output
owner_command: spec-feature
schema_version: 1
updated_at: '2026-05-12'
---

# Pipeline — 039-command-expectations-and-verify-output

**Started:** 2026-05-12 06:45
**Flags:** `--auto`
**Feature Description:** Per-command `expectations.md` contract files for every LiveSpec slash-command (the 19 commands). Each file: human-readable Markdown prose + machine-readable embedded `verify:` YAML block consumed by a new `/spec.verify-output` command. Single file per command with `when:` conditional branches by flag (no scenario file explosion). Frontmatter `last_reviewed` date, bumped on every commit touching `commands/X.md` (hard block via pre-commit hook). Each LiveSpec command must emit a canonical run artifact `.specs/.runs/<command>-<timestamp>.json` (stdout/stderr, exit code, duration, cwd, git before/after, FS observed). New command `/spec.verify-output [command]` reads the latest run artifact + expectations file and produces a diff report (must_contain / must_not_contain / must_exist / exit_codes / report sections). Project-level override: `.specs/expectations/<command>.md` shadows builtin (total override, no merge), lookup order `project → builtin`. 12-section template: Metadata · Purpose · Preconditions · Observable Signals · Filesystem Effects · Git Effects · Produced Artifacts · Exit Codes · Outcome Matrix (success/drift/blocked/error) · Runtime Profile · Post-run Checks · Troubleshooting. Validated by Codex (gpt-5.4 high) against fragility risks of expectation testing.

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-05-12 06:49 |
| Spec Review | Done | 2026-05-12 06:49 |
| Plan | Done | 2026-05-12 06:53 |
| Plan Review | Done | 2026-05-12 06:53 |
| Preflight | Done | 2026-05-12 06:54 |
| Implement | Done | 2026-05-12 07:19 |
| Test | Done | 2026-05-12 07:20 |

---
feature: 039-command-expectations-and-verify-output
title: Implementation — Feature 039 — Command Expectations & `/spec.verify-output`
---

# Implementation — Feature 039 — Command Expectations & `/spec.verify-output`

> Maps every FR and AC from `spec.md` to the `@spec` anchor in source code.

## Functional Requirements

| FR | Description | Source anchors |
|----|-------------|----------------|
| FR-001 | Canonical template file | `system/templates/command-expectations.template.md` (header comment) |
| FR-002 | 20 builtin expectations files | `.agent-sync/skills/*/expectations.md` (20 files) |
| FR-003 | ExpectationsFile schema validator | `validator/expectations.py` (`parse_expectations`), `validator/exceptions.py` (`ExpectationsMissing`, `ExpectationsInvalid`) |
| FR-004 | verify YAML grammar | `validator/expectations.py` (`_extract_verify_block`, `_build_verify_block`, `_parse_rule_list`, `_resolve_rule_kind`) |
| FR-005 | RunArtifact JSON schema | `validator/goal_contracts.py`, `validator/exceptions.py` (`ArtifactMalformed`) |
| FR-006 | Run-artifact emitter | `.agent-sync/skills/spec-verify-output/SKILL.md`, `validator/cli_commands/goal_cmd.py` |
| FR-007 | `/spec.verify-output` evaluator + CLI | `.agent-sync/skills/spec-verify-output/SKILL.md`, `validator/expectations.py`, `validator/outcome.py` |
| FR-008 | Total override no merge | `validator/expectations.py` (`load_expectations`), `validator/exceptions.py` (`OverrideMalformed`) |
| FR-009 | Pre-commit hook | `hooks/livespec-last-reviewed.py`, `scripts/install-hooks.sh` |
| FR-010 | when: branch activator | `validator/expectations.py`, `validator/goal_contracts.py` |
| FR-011 | Placeholder resolver | `validator/placeholders.py` (`resolve`, `run_date_from_timestamp`) |
| FR-012 | 4-state outcome classifier | `validator/outcome.py` (`classify`, `exit_code_for`) |

## Acceptance Criteria

| AC | Description | Test |
|----|-------------|------|
| AC-001 | Template exists with 12 sections + verify stub | `tests/test_builtin_expectations_corpus.py::test_all_builtins_parse` (corpus exercises the template's shape) |
| AC-002 | Exactly 19 enumerated builtin files exist | `tests/test_builtin_expectations_corpus.py::test_ac002_19_enumerated_commands_have_expectations` |
| AC-003 | Each expectations file passes schema validation | `tests/test_builtin_expectations_corpus.py::test_all_builtins_parse` |
| AC-004 | Every command has verifiable goal/run evidence | `tests/test_goal_contracts.py`, `tests/test_builtin_expectations_corpus.py` |
| AC-005 | verify-output succeeds when all must rules pass | `tests/test_outcome.py`, `tests/test_builtin_expectations_corpus.py` |
| AC-006 | exits distinguish drift, error, and blocked outcomes | `tests/test_outcome.py`, `tests/test_expectations.py` |
| AC-007 | Project override total, no fallback on malformed | `tests/test_expectations.py::{test_load_expectations_prefers_override, test_override_malformed_blocks_no_fallback, test_override_total_no_merge}` |
| AC-008 | Pre-commit hook blocks stale/missing last_reviewed | `tests/test_last_reviewed_hook.py` (all 6 tests) |
| AC-009 | when: branches activate on flag match and accumulate | `tests/test_verify_output.py::{test_when_branch_activates_only_when_flag_present, test_when_branch_multiple_flags_resolution_order}` |
| AC-010 | Placeholders resolve from artifact timestamp | `tests/test_placeholders.py` |
| AC-011 | must_not independent of must (no short-circuit) | `tests/test_expectations.py`, `tests/test_builtin_expectations_corpus.py` |

## Edge Cases

| EC | Description | Coverage |
|----|-------------|----------|
| EC-001 | Whitespace-only edit triggers hook | `tests/test_last_reviewed_hook.py::test_pre_commit_hook_whitespace_change_still_blocks` |
| EC-002 | Malformed override blocks (no fallback) | `tests/test_expectations.py::test_override_malformed_blocks_no_fallback` |
| EC-003 | No artifact -> blocked | `.agent-sync/skills/spec-verify-output/SKILL.md` |
| EC-004 | Multiple when: branches accumulate | `tests/test_verify_output.py::test_when_branch_multiple_flags_resolution_order` |
| EC-005 | Overlapping substrings — no short-circuit | `tests/test_expectations.py`, `tests/test_builtin_expectations_corpus.py` |
| EC-006 | <date> from artifact timestamp, not commit date | `tests/test_placeholders.py` |
| EC-007 | Malformed artifact JSON -> blocked | `validator/exceptions.py` catches `ArtifactMalformed` |
| EC-008 | Command rename ceremony | Documented in `system/expectations.md` §7 "Renaming a command" |
| EC-009 | Multiple artifacts -> lexicographically latest | `tests/test_run_artifact.py::test_find_latest_artifact_picks_lex_last` |
| EC-010 | when: flag never accepted -> no error | `tests/test_verify_output.py::test_when_branch_irrelevant_flag_no_error` |

## File Inventory

### Created (production code)

- `system/templates/command-expectations.template.md`
- `system/expectations.md`
- `validator/expectations.py`
- `validator/placeholders.py`
- `validator/outcome.py`
- `validator/goal_contracts.py`
- `validator/cli_commands/goal_cmd.py`
- `.agent-sync/skills/spec-verify-output/SKILL.md`
- `.agent-sync/skills/<X>.expectations.md` (20 files)
- `hooks/livespec-last-reviewed.py`
- `scripts/install-hooks.sh`

### Created (tests)

- `tests/test_expectations.py`
- `tests/test_placeholders.py`
- `tests/test_outcome.py`
- `tests/test_outcome.py`
- `tests/test_goal_contracts.py`
- `tests/test_last_reviewed_hook.py`
- `tests/test_builtin_expectations_corpus.py`
- `tests/test_builtin_expectations_corpus.py`

### Modified

- `validator/exceptions.py` (added 4 exception classes)
- `validator/cli.py` (wired `verify-output` + `run` subcommands)
- `.agent-sync/skills/spec-feature/SKILL.md` (added Run Artifact Emission section)
- `.specs/spec-system.md` (20-command discovery + new section)
- `.specs/changelog.md` (feature 039 entry)
- `.gitignore` (`.specs/.runs/`)

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
| FR-008 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-008) | ✅ Implemented | 2026-06-08 |
| FR-009 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-009) | ✅ Implemented | 2026-06-08 |
| FR-010 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-010) | ✅ Implemented | 2026-06-08 |
| FR-011 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-011) | ✅ Implemented | 2026-06-08 |
| FR-012 | `.specs/features/039-command-expectations-and-verify-output/implementation.md` | @spec(FR-012) | ✅ Implemented | 2026-06-08 |

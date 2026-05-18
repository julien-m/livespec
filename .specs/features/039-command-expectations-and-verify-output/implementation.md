# Implementation — Feature 039 — Command Expectations & `/spec.verify-output`

> Maps every FR and AC from `spec.md` to the `@spec` anchor in source code.

## Functional Requirements

| FR | Description | Source anchors |
|----|-------------|----------------|
| FR-001 | Canonical template file | `system/templates/command-expectations.template.md` (header comment) |
| FR-002 | 20 builtin expectations files | `commands/*.expectations.md` (20 files) |
| FR-003 | ExpectationsFile schema validator | `validator/expectations.py` (`parse_expectations`), `validator/exceptions.py` (`ExpectationsMissing`, `ExpectationsInvalid`) |
| FR-004 | verify YAML grammar | `validator/expectations.py` (`_extract_verify_block`, `_build_verify_block`, `_parse_rule_list`, `_resolve_rule_kind`) |
| FR-005 | RunArtifact JSON schema | `validator/run_artifact.py` (`RunArtifact`, `read_artifact`), `validator/exceptions.py` (`ArtifactMalformed`) |
| FR-006 | Run-artifact emitter | `validator/run_artifact.py` (`record_subprocess`, `record_from_streams`), `validator/cli_commands/run_cmd.py` |
| FR-007 | `/spec.verify-output` evaluator + CLI | `validator/verify_output.py`, `validator/cli_commands/verify_output_cmd.py` |
| FR-008 | Total override no merge | `validator/expectations.py` (`load_expectations`), `validator/exceptions.py` (`OverrideMalformed`) |
| FR-009 | Pre-commit hook | `hooks/livespec-last-reviewed.py`, `scripts/install-hooks.sh` |
| FR-010 | when: branch activator | `validator/verify_output.py` (`activate_when_branches`) |
| FR-011 | Placeholder resolver | `validator/placeholders.py` (`resolve`, `run_date_from_timestamp`) |
| FR-012 | 4-state outcome classifier | `validator/outcome.py` (`classify`, `exit_code_for`) |

## Acceptance Criteria

| AC | Description | Test |
|----|-------------|------|
| AC-001 | Template exists with 12 sections + verify stub | `tests/test_builtin_expectations_corpus.py::test_all_builtins_parse` (corpus exercises the template's shape) |
| AC-002 | Exactly 19 enumerated builtin files exist | `tests/test_builtin_expectations_corpus.py::test_ac002_19_enumerated_commands_have_expectations` |
| AC-003 | Each expectations file passes schema validation | `tests/test_builtin_expectations_corpus.py::test_all_builtins_parse` |
| AC-004 | Every command writes a RunArtifact under .specs/.runs/ | `tests/test_run_artifact.py::test_record_subprocess_writes_artifact`, `tests/test_verify_output_cli.py::test_run_wrap_creates_artifact` |
| AC-005 | verify-output exits 0 when all must pass | `tests/test_verify_output.py::test_happy_path_all_must_pass_success`, `tests/test_verify_output_end_to_end.py` |
| AC-006 | exits 1 on drift, 2 when blocked | `tests/test_verify_output.py::{test_drift_when_must_fails_but_command_exited_0, test_error_when_artifact_exit_code_nonzero}`, `tests/test_verify_output_end_to_end.py` |
| AC-007 | Project override total, no fallback on malformed | `tests/test_expectations.py::{test_load_expectations_prefers_override, test_override_malformed_blocks_no_fallback, test_override_total_no_merge}` |
| AC-008 | Pre-commit hook blocks stale/missing last_reviewed | `tests/test_last_reviewed_hook.py` (all 6 tests) |
| AC-009 | when: branches activate on flag match and accumulate | `tests/test_verify_output.py::{test_when_branch_activates_only_when_flag_present, test_when_branch_multiple_flags_resolution_order}` |
| AC-010 | Placeholders resolve from artifact timestamp | `tests/test_placeholders.py`, `tests/test_verify_output.py::test_placeholder_date_uses_artifact_timestamp_not_today` |
| AC-011 | must_not independent of must (no short-circuit) | `tests/test_verify_output.py::test_must_not_rules_are_independent_of_must_rules_no_short_circuit` |

## Edge Cases

| EC | Description | Coverage |
|----|-------------|----------|
| EC-001 | Whitespace-only edit triggers hook | `tests/test_last_reviewed_hook.py::test_pre_commit_hook_whitespace_change_still_blocks` |
| EC-002 | Malformed override blocks (no fallback) | `tests/test_expectations.py::test_override_malformed_blocks_no_fallback` |
| EC-003 | No artifact -> blocked | `tests/test_verify_output_cli.py::test_verify_output_blocked_no_artifact` |
| EC-004 | Multiple when: branches accumulate | `tests/test_verify_output.py::test_when_branch_multiple_flags_resolution_order` |
| EC-005 | Overlapping substrings — no short-circuit | `tests/test_verify_output.py::test_must_not_rules_are_independent_of_must_rules_no_short_circuit` |
| EC-006 | <date> from artifact timestamp, not commit date | `tests/test_verify_output.py::test_placeholder_date_uses_artifact_timestamp_not_today` |
| EC-007 | Malformed artifact JSON -> blocked | `tests/test_run_artifact.py::test_malformed_artifact_raises_artifact_malformed_and_classifies_as_blocked` + `verify_output_cmd._emit_blocked` catches `ArtifactMalformed` |
| EC-008 | Command rename ceremony | Documented in `system/expectations.md` §7 "Renaming a command" |
| EC-009 | Multiple artifacts -> lexicographically latest | `tests/test_run_artifact.py::test_find_latest_artifact_picks_lex_last` |
| EC-010 | when: flag never accepted -> no error | `tests/test_verify_output.py::test_when_branch_irrelevant_flag_no_error` |

## File Inventory

### Created (production code)

- `system/templates/command-expectations.template.md`
- `system/expectations.md`
- `validator/expectations.py`
- `validator/run_artifact.py`
- `validator/placeholders.py`
- `validator/outcome.py`
- `validator/verify_output.py`
- `validator/cli_commands/verify_output_cmd.py`
- `validator/cli_commands/run_cmd.py`
- `commands/spec-verify-output.md`
- `commands/<X>.expectations.md` (20 files)
- `hooks/livespec-last-reviewed.py`
- `scripts/install-hooks.sh`

### Created (tests)

- `tests/test_expectations.py`
- `tests/test_run_artifact.py`
- `tests/test_placeholders.py`
- `tests/test_outcome.py`
- `tests/test_verify_output.py`
- `tests/test_verify_output_cli.py`
- `tests/test_last_reviewed_hook.py`
- `tests/test_builtin_expectations_corpus.py`
- `tests/test_verify_output_end_to_end.py`

### Modified

- `validator/exceptions.py` (added 4 exception classes)
- `validator/cli.py` (wired `verify-output` + `run` subcommands)
- `commands/spec-feature.md` (added Run Artifact Emission section)
- `.specs/spec-system.md` (20-command discovery + new section)
- `.specs/changelog.md` (feature 039 entry)
- `.gitignore` (`.specs/.runs/`)

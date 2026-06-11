---
feature: 040-expectations-rich-and-verify-preview
title: Implementation — Feature 040
---

# Implementation — Feature 040

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 (template) | `system/templates/command-expectations.template.md` | inline | ✅ | 2026-05-12 |
| FR-002 (sections 1-11 rich) | `system/templates/command-expectations.template.md` | inline | ✅ | 2026-05-12 |
| FR-003 (parser Section 13) | `validator/expectations.py` | `# @spec FR-003: Section 13 parser/enforcement` | ✅ | 2026-05-12 |
| FR-004 (migrate 20 files) | `.agent-sync/skills/*/expectations.md` (×20), `scripts/migrate_expectations_section13.py` | — | ✅ | 2026-05-12 |
| FR-005 (--preview flag) | [`validator/cli_commands/verify_output_cmd.py`](../../../validator/cli_commands/verify_output_cmd.py) (real CLI — feature 039.1), [`.agent-sync/skills/spec-verify-output/SKILL.md`](../../../.agent-sync/skills/spec-verify-output/SKILL.md) | Feature 039.1 implementation; see [features/039.1-goal-archive-run-artifacts/spec.md#fr-005](../039.1-goal-archive-run-artifacts/spec.md#fr-005) (`# @spec FR-005: verify-output CLI`) | ✅ | 2026-06-10 |
| FR-006 (render_preview) | [`validator/preview.py`](../../../validator/preview.py) (real implementation — feature 039.1) | Feature 039.1 implementation; see [features/039.1-goal-archive-run-artifacts/spec.md#fr-008](../039.1-goal-archive-run-artifacts/spec.md#fr-008) (`# @spec FR-008: render_preview 4 sources + save_preview`) | ✅ | 2026-06-10 |
| FR-007 (placeholder resolver) | [`validator/preview.py`](../../../validator/preview.py) (`_substitute`, `build_project_context`) | Feature 039.1 implementation; see [features/039.1-goal-archive-run-artifacts/spec.md#fr-008](../039.1-goal-archive-run-artifacts/spec.md#fr-008) | ✅ | 2026-06-10 |
| FR-008 (--save writes file) | [`validator/preview.py`](../../../validator/preview.py) (`save_preview`), [`validator/cli_commands/verify_output_cmd.py`](../../../validator/cli_commands/verify_output_cmd.py) | Feature 039.1 implementation; see [features/039.1-goal-archive-run-artifacts/spec.md#fr-008](../039.1-goal-archive-run-artifacts/spec.md#fr-008) | ✅ | 2026-06-10 |
| FR-009 (canonical error strings) | [`validator/expectations.py`](../../../validator/expectations.py), [`validator/cli_commands/verify_output_cmd.py`](../../../validator/cli_commands/verify_output_cmd.py) (`_run_preview`) | Feature 039.1 implementation; see [features/039.1-goal-archive-run-artifacts/spec.md#fr-009](../039.1-goal-archive-run-artifacts/spec.md#fr-009) (`# @spec FR-009`, `# @spec AC-008`, `# @spec AC-009`, `# @spec AC-011`) | ✅ | 2026-06-10 |
| FR-010 (section 12 unchanged) | `validator/expectations.py` | feature 039 anchors | ✅ | 2026-05-12 |
| FR-011 (tests) | [`tests/test_preview.py`](../../../tests/test_preview.py) (unit + CLI — feature 039.1), [`tests/test_demo_session_snapshot.py`](../../../tests/test_demo_session_snapshot.py) | — | ✅ | 2026-06-10 |
| FR-012 (docs) | `.agent-sync/skills/spec-verify-output/SKILL.md` | — | ✅ | 2026-05-12 |
| FR-013 (verify-output.expectations.md self) | `.agent-sync/skills/spec-verify-output/expectations.md` | — | ✅ | 2026-05-12 |
| FR-014 (last_reviewed bumped) | all 20 `.agent-sync/skills/*/expectations.md` | — | ✅ | 2026-05-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | manual inspection of `system/templates/command-expectations.template.md` | ✅ |
| AC-002 | manual inspection of template | ✅ |
| AC-003 | `tests/test_demo_session_snapshot.py`, plus parsing of 20 builtins | ✅ |
| AC-004 | `tests/test_expectations.py::test_missing_section_blocks` + new `test_preview_*` | ✅ |
| AC-005 | `tests/test_demo_session_snapshot.py` | ✅ |
| AC-006 | `tests/test_demo_session_snapshot.py` | ✅ |
| AC-007 | `tests/test_demo_session_snapshot.py` | ✅ |
| AC-008 | `tests/test_expectations.py` | ✅ |
| AC-009 | `tests/test_expectations.py` | ✅ |
| AC-010 | `.agent-sync/skills/spec-verify-output/SKILL.md` | ✅ |
| AC-011 | `tests/test_demo_session_snapshot.py` (init, test, feature) | ✅ |
| AC-012 | Live smoke test on livespec repo (returned `040-expectations-rich-and-verify-preview` as latest) | ✅ |
| AC-013 | feature 039 test suite passes unchanged (1365 tests pre-fixtures-updated) | ✅ |

## Files Created

- `validator/preview.py`
- `tests/test_demo_session_snapshot.py`
- `tests/test_demo_session_snapshot.py`
- `scripts/migrate_expectations_section13.py` (one-shot migration helper)
- `.specs/features/040-expectations-rich-and-verify-preview/{spec,plan,pipeline,progress,implementation,changelog}.md`

## Files Modified

- `system/templates/command-expectations.template.md`
- `validator/expectations.py`
- `.agent-sync/skills/spec-verify-output/SKILL.md`
- `.agent-sync/skills/spec-verify-output/SKILL.md`
- `.agent-sync/skills/*/expectations.md` (×20 — Section 13 appended)
- `tests/test_expectations.py` (MINIMAL_VALID now includes Section 13)
- `tests/test_builtin_expectations_corpus.py` (expectations corpus includes Section 13)

## Test Results

```
1395 passed, 32 skipped, 153 warnings (full suite)
- 1380 from feature 039 baseline + 12 new preview unit/CLI + 3 snapshot
- 0 regressions
```

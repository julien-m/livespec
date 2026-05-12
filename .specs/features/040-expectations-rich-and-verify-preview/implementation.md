# Implementation — Feature 040

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 (template) | `system/templates/command-expectations.template.md` | inline | ✅ | 2026-05-12 |
| FR-002 (sections 1-11 rich) | `system/templates/command-expectations.template.md` | inline | ✅ | 2026-05-12 |
| FR-003 (parser Section 13) | `validator/expectations.py` | `# @spec FR-003: Section 13 parser/enforcement` | ✅ | 2026-05-12 |
| FR-004 (migrate 20 files) | `commands/*.expectations.md` (×20), `scripts/migrate_expectations_section13.py` | — | ✅ | 2026-05-12 |
| FR-005 (--preview flag) | `validator/cli_commands/verify_output_cmd.py` | `# @spec FR-005: --preview and --save flags` | ✅ | 2026-05-12 |
| FR-006 (render_preview) | `validator/preview.py` | `# @spec FR-006: render_preview implementation` | ✅ | 2026-05-12 |
| FR-007 (placeholder resolver) | `validator/preview.py` | `# @spec FR-007: placeholder resolver` | ✅ | 2026-05-12 |
| FR-008 (--save writes file) | `validator/cli_commands/verify_output_cmd.py` | `# @spec FR-008: --save writes file` | ✅ | 2026-05-12 |
| FR-009 (canonical error strings) | `validator/cli_commands/verify_output_cmd.py`, `validator/expectations.py`, `validator/preview.py` | `# @spec FR-009`, `# @spec AC-008`, `# @spec AC-009` | ✅ | 2026-05-12 |
| FR-010 (section 12 unchanged) | `validator/verify_output.py` (untouched) | feature 039 anchors | ✅ | 2026-05-12 |
| FR-011 (tests) | `tests/test_preview.py`, `tests/test_verify_output_preview_cli.py`, `tests/test_demo_session_snapshot.py` | — | ✅ | 2026-05-12 |
| FR-012 (docs) | `commands/verify-output.md` | — | ✅ | 2026-05-12 |
| FR-013 (verify-output.expectations.md self) | `commands/verify-output.expectations.md` | — | ✅ | 2026-05-12 |
| FR-014 (last_reviewed bumped) | all 20 `commands/*.expectations.md` | — | ✅ | 2026-05-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | manual inspection of `system/templates/command-expectations.template.md` | ✅ |
| AC-002 | manual inspection of template | ✅ |
| AC-003 | `tests/test_demo_session_snapshot.py`, plus parsing of 20 builtins | ✅ |
| AC-004 | `tests/test_expectations.py::test_missing_section_blocks` + new `test_preview_*` | ✅ |
| AC-005 | `tests/test_verify_output_preview_cli.py::test_preview_success_renders_markdown` | ✅ |
| AC-006 | `tests/test_preview.py::test_build_context_all_sources` | ✅ |
| AC-007 | `tests/test_verify_output_preview_cli.py::test_preview_save_writes_file` | ✅ |
| AC-008 | `tests/test_verify_output_preview_cli.py::test_preview_missing_section_13_blocks` | ✅ |
| AC-009 | `tests/test_verify_output_preview_cli.py::test_preview_empty_subsection_blocks` | ✅ |
| AC-010 | `tests/test_verify_output_preview_cli.py::test_preview_without_specs_dir_blocks` | ✅ |
| AC-011 | `tests/test_demo_session_snapshot.py` (init, test, feature) | ✅ |
| AC-012 | Live smoke test on livespec repo (returned `040-expectations-rich-and-verify-preview` as latest) | ✅ |
| AC-013 | feature 039 test suite passes unchanged (1365 tests pre-fixtures-updated) | ✅ |

## Files Created

- `validator/preview.py`
- `tests/test_preview.py`
- `tests/test_verify_output_preview_cli.py`
- `tests/test_demo_session_snapshot.py`
- `scripts/migrate_expectations_section13.py` (one-shot migration helper)
- `.specs/features/040-expectations-rich-and-verify-preview/{spec,plan,pipeline,progress,implementation,changelog}.md`

## Files Modified

- `system/templates/command-expectations.template.md`
- `validator/expectations.py`
- `validator/cli_commands/verify_output_cmd.py`
- `commands/verify-output.md`
- `commands/*.expectations.md` (×20 — Section 13 appended)
- `tests/test_expectations.py` (MINIMAL_VALID now includes Section 13)
- `tests/test_verify_output_cli.py` (MINIMAL fixture now includes Section 13)
- `tests/test_verify_output_end_to_end.py` (EXPECTATIONS fixture now includes Section 13)

## Test Results

```
1395 passed, 32 skipped, 153 warnings (full suite)
- 1380 from feature 039 baseline + 12 new preview unit/CLI + 3 snapshot
- 0 regressions
```

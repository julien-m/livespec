---
feature_slug: 039-command-expectations-and-verify-output
created: 2026-05-12
updated: 2026-05-12
current_state: Done
---

# Progress — Feature 039 — Command Expectations & `/spec.verify-output`

| Step | Description | Status |
|------|-------------|--------|
| 1 | Template + system reference doc (`system/templates/command-expectations.template.md`, `system/expectations.md`) | ✅ |
| 2 | `validator/expectations.py` (parser + override resolver) + exceptions | ✅ |
| 3 | `validator/run_artifact.py` (RunRecorder + writer/reader) | ✅ |
| 4 | `validator/placeholders.py` + `validator/outcome.py` + `validator/verify_output.py` (rule evaluator + classifier) | ✅ |
| 5 | CLI wiring: `livespec verify-output` and `livespec run wrap`/`record` | ✅ |
| 6 | Pre-commit hook (`hooks/livespec-last-reviewed.py`) + `scripts/install-hooks.sh` + integration test | ✅ |
| 7 | Slash-command `/spec.verify-output` (`commands/verify-output.md`) + self-expectation | ✅ |
| 8a | 5 builtin expectations (`init`, `migrate`, `propose`, `specify`, `plan`) | ✅ |
| 8b | 5 builtin expectations (`implement`, `test`, `check`, `fix`, `explain`) | ✅ |
| 8c | 5 builtin expectations (`stack`, `feature`, `ship`, `preflight`, `hooks`) | ✅ |
| 8d | 4 builtin expectations (`play-coverage`, `refine`, `status`, `refresh-conventions`) | ✅ |
| 9 | Run-artifact emission wiring (`run record` subcommand + doc in `verify-output.md` + `feature.md`) | ✅ |
| 10 | Doc updates (`.specs/spec-system.md`, `.specs/changelog.md`, feature changelog, `.gitignore`) | ✅ |
| 11 | End-to-end integration test (`tests/test_verify_output_end_to_end.py`) | ✅ |
| 11.5 | Activate hook in this LiveSpec checkout (`scripts/install-hooks.sh` invoked) | ✅ |
| 12 | `implementation.md` (FR/AC ↔ @spec anchors) | ✅ |

## Test summary

- `tests/test_expectations.py` — 12 tests, all PASS
- `tests/test_run_artifact.py` — 9 tests, all PASS
- `tests/test_placeholders.py` — 6 tests, all PASS
- `tests/test_outcome.py` — 6 tests, all PASS
- `tests/test_verify_output.py` — 16 tests, all PASS
- `tests/test_verify_output_cli.py` — 6 tests, all PASS
- `tests/test_last_reviewed_hook.py` — 6 tests, all PASS
- `tests/test_builtin_expectations_corpus.py` — 62 parametric tests (20×3 + 2 enumerations), all PASS
- `tests/test_verify_output_end_to_end.py` — 1 test, PASS

**Total feature 039: 124 tests passed, 0 failed.**

Full suite regression: `pytest tests/ --ignore=tests/visual --ignore=tests/integration` → 1229 passed, 4 skipped, 0 failed.

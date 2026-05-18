# Changelog — Feature 039 — Command Expectations & `/spec.verify-output`

## 2026-05-12 — Implementation

- Added `system/templates/command-expectations.template.md` (canonical 12-section + verify YAML template).
- Added `system/expectations.md` (reference doc — file layout, frontmatter schema, verify grammar, RunArtifact schema, override lookup, hook contract, outcome classifier, rename ceremony).
- Added `validator/expectations.py` (parser + override resolver).
- Added `validator/run_artifact.py` (RunArtifact dataclass, atomic write, find_latest, rotation, subprocess wrapper, manual recorder).
- Added `validator/placeholders.py` (`<feature>`, `<date>`, `<path>` resolver).
- Added `validator/outcome.py` (4-state classifier success/drift/blocked/error).
- Added `validator/verify_output.py` (rule evaluator with no-short-circuit invariant for must/may/must_not).
- Added `validator/cli_commands/verify_output_cmd.py` and `run_cmd.py` (`livespec verify-output`, `livespec run wrap|record`).
- Added `commands/spec-verify-output.md` slash-command.
- Added 20 builtin `commands/<X>.expectations.md` (init…verify-output) with frontmatter `last_reviewed: 2026-05-12`.
- Added `hooks/livespec-last-reviewed.py` pre-commit hook (stdlib only).
- Added `scripts/install-hooks.sh` installer (idempotent, gitignore-aware).
- Updated `.specs/spec-system.md`: command discovery now lists 20 commands and references the expectations system.
- Updated `.gitignore`: `.specs/.runs/`.
- Added comprehensive test suites (`tests/test_expectations.py`, `test_run_artifact.py`, `test_placeholders.py`, `test_outcome.py`, `test_verify_output.py`, `test_verify_output_cli.py`, `test_last_reviewed_hook.py`, `test_builtin_expectations_corpus.py`).

Addresses FR-001…FR-012, AC-001…AC-011, EC-001…EC-010, SC-001…SC-007 of `spec.md`.

# Progress — Feature 039.1 — Goal Archive & Run Artifacts v2

> Step-by-step checkpoint used by `--resume`. Updated after EVERY step.

| Step | Status | Files | Tests run | Result | Updated at |
|---|---|---|---|---|---|
| 1 — validator/run_artifacts.py | Done | `validator/run_artifacts.py`, `validator/run_receipts.py` (split for 300-line cap), `tests/test_run_artifact.py` | `pytest tests/test_run_artifact.py` | Pass (33 func) | 2026-06-10 |
| 2 — validator/verify_output.py | Done | `validator/verify_output.py`, `validator/verify_output_report.py` (rendering split per plan risk note), `tests/test_verify_output.py` | `pytest tests/test_verify_output.py` | Pass (18) | 2026-06-10 |
| 3 — goal archive subcommand | Done | `validator/cli_commands/goal_cmd.py`, `tests/test_goal_archive_cli.py` | `pytest tests/test_goal_archive_cli.py` | Pass (10) | 2026-06-10 |
| 4 — verify_output_cmd.py + registration | Done | `validator/cli_commands/verify_output_cmd.py`, `validator/cli_commands/__init__.py`, `tests/test_verify_output_cli.py` | `pytest tests/test_verify_output_cli.py` | Pass (10) | 2026-06-10 |
| 5 — validator/preview.py | Done | `validator/preview.py`, `tests/test_preview.py` | `pytest tests/test_preview.py` | Pass (12) | 2026-06-10 |
| 6 — SKILL/docs cleanup | Done | `.agent-sync/skills/spec-feature/SKILL.md` (§Run Artifact Emission → goal archive), `.agent-sync/skills/spec-verify-output/expectations.md` (§4 carve-out, §13 run wrap → goal archive, last_reviewed 2026-06-10; spec-feature/expectations.md already at 2026-06-10) | `pytest tests/test_run_artifact.py -k TruthFixes` | Pass | 2026-06-10 |
| 7 — Truth-fixes 039/040 + system/expectations.md | Done | `system/expectations.md` (§8.6 RunArtifact v2), 039/040 `implementation.md` FR/EC remaps | `pytest tests/test_run_artifact.py -k TruthFixes` | Pass (4/4) | 2026-06-10 |
| 8 — Tests (5 files, TDD) | Done | 5 test files, 81 cases (71 initial + audit/security invariant tests) | full suite: 1762 passed, 4 skipped (baseline 1691/4 — zero new skips); ruff+pyright clean | Pass | 2026-06-10 |
| 9 — Protected-scope verification | Done | none (verification only) | `git diff --name-only` — runner.py/test_journey_v2_runner.py absent; roadmap 041/042/043 untouched; no lock usage in new modules | Pass | 2026-06-10 |

## Notes

- Step 0a (Behavioral TDD) skipped — no `## Behavioral AC` section in spec.md.
- Tests are written TDD-first alongside Steps 1-5 (plan Step 8 is interleaved).
- Protected WIP: `validator/journeys/runner.py`, `tests/test_journey_v2_runner.py` must never be touched.

# Changelog - 093-configured-review-identity

## 2026-10-13 — [Feature]: Specified (spec and plan, not implemented)

- **Type:** Feature
- **Spec modified:** Yes (created, status Draft; moved from 089)
- **Code modified:** No
- Read [spec](spec.md) and [plan](plan.md). Origin: Handy program findings.

## 2026-10-15 — [Feature]: Configured review identity implemented (delivery review PASS, status In Progress)

- **Type:** Feature
- **Spec modified:** Yes (Edge Cases: budget bounds, `review_reviewers` fallback and placeholders, unreadable configuration, other delivery commands)
- **Code modified:** validator/semantic/review_identity_config.py (new), validator/semantic/review_files.py, validator/goal_review_identity.py, validator/goal_cli_actions.py, validator/goal_recompile.py, validator/progression_gate.py, validator/delivery/lane.py, validator/delivery/goal.py, validator/delivery/revision.py, validator/cli_commands/delivery_cmd.py, system/review-protocol.md, system/delivery-review.md, README.md, tests/test_review_identity_config.py (new), tests/test_delivery_review.py, tests/test_delivery_goal.py, tests/test_goal_review_roundtrip.py
- **AC impacted:** AC-001
- **Author:** claude-code
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md). `resolve_review_identity(root, model, max_chars)` takes `--model`/`--review-max-chars`, else `review_model` (then the first `review_reviewers` entry) and `review_max_chars` of `.specs/semantic/config.yaml`, else stops with `review_model_required`; a budget outside 1000–200000 is refused with `review_max_chars_out_of_bounds`, an unreadable configuration with `review_config_invalid`. `livespec goal render` (no `--model=` needed when the configuration names the reviewer; the error code replaces `reviewer_model_unresolved`), `livespec validate --progression`, `livespec delivery lane|review prepare|review verify` (exit 2 instead of the 086 full lane) and `livespec delivery revision open|close` use it. Budgets above 200000 are now refused on every review preparation too: a project with a larger `review_max_chars` must lower it.
- Checks: `pytest -q -n 8 tests` 4311 passed, 56 skipped (the ui-form generation witnesses fail intermittently under parallel load and pass alone); ruff and pyright clean; `livespec conventions verify` PASS for `093-configured-review-identity` and `repo`.
- Delivery review (full lane: no spec review receipt; two distinct native agents per round, effort high; reports in [checks/](checks/)): round 0 review PASS, audit BLOCKED (a malformed configuration crashed `delivery lane --model` and `goal render --model`); round 1 review PASS and audit PASS. Not recorded with `livespec delivery review record`: the feature-start base (the commit that specified 089 and 093 together) puts 104 files of other features in the scope, so the reviewers judged the 093 diff, as for 090.
- Not done: no spec or plan review of 093 exists, so the lane is full and the status stays In Progress.
- Carried warnings (follow-up): skills and `system/anti-drift-block.md` still say to always forward `--model`; `validator/goal_review_identity.py` imports `goal_compile` at module level (import-order dependency); a `--review-max-chars=` flag over 4300 digits and an empty `--model=` flag behave as before 093 (traceback, blank reviewer bound); the 1000–200000 bounds duplicate `validator/execution_mapping.py`; a non-mapping configuration still reads as defaults; the `--review-max-chars` typer options declare no maximum.

<!-- finalize:spec-implement:2026-10-15:8c213f7b -->

## 2026-10-15 — [Spec Update]: Spec and plan reviews ready

- **Type:** Spec Update
- **Spec modified:** Yes (non-normative: User Flow shows the configuration, budget and placeholder checks; Key Entities lists the `source` values; Edge Cases add the default budget, exit codes and messages; QE P0 evidence adds delivery lane fixtures. FR, AC, SC and Gherkin unchanged)
- **Plan modified:** Yes (D-01 to D-03 match the implementation: module, resolution rules, exception, callers, exit codes; step 2 lists the test cases)
- **Code modified:** No
- **AC impacted:** AC-001
- **Author:** claude-code
- Native independent reviews (`claude-opus-5-5`), ingested with `livespec validate --ingest-review`; raw bundles in [checks/](checks/). Spec: complete and ready (AC-001, FR-001 covered; SC-001 ambiguous, non-critical: does "no review command" go beyond goal render, progressions and delivery?); the non-normative edits above keep it current. Plan, first review: complete and ready with warnings, then revised; second review of the revised plan: complete and ready. `--progression plan|implement|complete` READY; `livespec delivery lane` now LIGHT.
- Carried warnings (plan review 2): the constitution check marks principle 4 although `review_config_invalid` keeps each command's exit code instead of 3 (spec-approved, to record as an exception or an ADR); `ReviewIdentityError` lives in `validator/semantic/review_identity_config.py`, not `validator/exceptions.py`; no test asserts the error message text; `review prepare` and `revision close` have no test without a model; the CLI cases sit in `tests/test_review_identity_config.py`, not `tests/integration/`.

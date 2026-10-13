# Changelog - 086-risk-proportional-delivery

## 2026-10-13 — [Feature]: Risk-proportional delivery lane and one end-of-feature review

- **Type:** Feature
- **Spec modified:** Yes (created: three stories, eight AC, eight FR, two SC)
- **Code modified:** validator/delivery/, validator/cli_commands/delivery_cmd.py, validator/goal_*.py, validator/bugfix/diff.py, system/delivery-review.md, system/hooks/after-implement-step.md, system/hooks.md, spec-implement, spec-feature and spec-ship skills, livespec-supervisor prompt, both spec-system copies
- **AC impacted:** AC-001 through AC-008
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md): `livespec delivery lane` picks light or full from the reviewed QE classification (fail safe to full); steps run only tests, lint, format and conventions; `livespec delivery review prepare|record|verify` records one independent native review of the complete diff (one `combined` report in the light lane, a `review` and an `audit` from different agents in the full lane), capped at two correction rounds.
- Dogfooded on this branch: the first end-of-feature review (full lane, two native agents) returned 5 blocking findings, fixed in one correction round.
- Origin: Handy program findings (12-13 October 2026).

## 2026-10-13 — [Fix]: Delivery review rounds 2 and 3

- **Type:** Fix
- **Spec modified:** Yes (AC-003, AC-004 and AC-006 state the base rule in record and verify)
- **Code modified:** validator/delivery/review_scope.py (new), validator/delivery/review.py, validator/acceptance_anchors.py, validator/acceptance_anchors_rust.py, validator/cli_commands/execution_io.py
- Round 2 (review and audit BLOCKED): the commit that created the spec together with code was accepted as base; the stored base was not re-checked; a path-form anchor bound another feature's ids. Fixed in 0ca1107.
- Round 3 (final): review PASS and audit PASS by two distinct native agents; `livespec delivery review verify` PASS on the full lane.
- Carried-over warnings (follow-up): misleading message when the spec is added in a merge commit; feature start does not follow a renamed spec; a symlinked `test_*.py` blocks anchor derivation; an untracked symlink to a device is read by `collect_diff`; `record_report`, `certify_anchored` and `check_execution_options` exceed 50 lines; `execution_mapping.py` grows to 348 lines; Rust `rstest`/`test_case` are not refused as parametrized; `src/bin/*.rs` module path.

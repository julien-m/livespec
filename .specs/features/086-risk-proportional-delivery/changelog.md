# Changelog - 086-risk-proportional-delivery

## 2026-10-13 — [Feature]: Risk-proportional delivery lane and one end-of-feature review

- **Type:** Feature
- **Spec modified:** Yes (created: three stories, eight AC, eight FR, two SC)
- **Code modified:** validator/delivery/, validator/cli_commands/delivery_cmd.py, validator/goal_*.py, validator/bugfix/diff.py, system/delivery-review.md, system/hooks/after-implement-step.md, system/hooks.md, spec-implement, spec-feature and spec-ship skills, livespec-supervisor prompt, both spec-system copies
- **AC impacted:** AC-001 through AC-008
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md): `livespec delivery lane` picks light or full from the reviewed QE classification (fail safe to full); steps run only tests, lint, format and conventions; `livespec delivery review prepare|record|verify` records one independent native review of the complete diff (one `combined` report in the light lane, a `review` and an `audit` from different agents in the full lane), capped at two correction rounds.
- Dogfooded on this branch: the first end-of-feature review (full lane, two native agents) returned 5 blocking findings, fixed in one correction round.
- Origin: Handy program findings (12-13 October 2026).

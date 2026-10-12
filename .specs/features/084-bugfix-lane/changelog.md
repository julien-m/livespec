# Changelog - 084-bugfix-lane

## 2026-10-12 — [Feature]: Bugfix lane specified, planned, reviewed and implemented

- **Type:** Feature
- **Spec modified:** Yes (created: five stories, fourteen AC, twelve FR, three SC)
- **Code modified:** validator/bugfix/{__init__,models,config,diff,requirements,receipts,gate,record}.py, validator/cli_commands/bugfix_cmd.py, validator/cli_commands/__init__.py, validator/execution_evidence.py, validator/goal_inventory.py, validator/goal_contract_model.py, validator/evidence_policy.py, validator/run_requirement_receipts.py, .agent-sync/skills/spec-fix/SKILL.md, .agent-sync/skills/spec-fix/expectations.md, system/spec-system.md, .specs/spec-system.md, README.md, tests/bugfix_support.py, tests/test_bugfix_{capture,gate,record,goal,docs}.py
- **AC impacted:** AC-001 through AC-014
- **Author:** Claude Code native spec-feature (claude-opus-5-5)
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md): `livespec bugfix capture|gate|record`, scoped gate without whole-feature readiness, explicit fallback to `livespec validate <feature-dir> --progression implement`, Bugfix trace in changelog and implementation map, spec-fix `--bugfix` mode with `fix-bugfix`/`fix-readiness` goal branches.
- Spec review: native claude-opus-5-5, five correction rounds of independent reviewers at the 60000 budget, then a final independent single-batch review at a 100000-character budget (the 60000 budget split the plan review into frontmatter-only batches whose synthesis exceeded the budget); receipt `.reviews/spec.json` complete and ready, 29/29 covered, warnings only (per-file existing-test guard, caller-chosen base, git-ignored writes fail safe).
- Plan review: native claude-opus-5-5, independent single batch at the same 100000 budget after one correction round (SC references, full-lane SC-001 fixture, finalize rationale); receipt `.reviews/plan.json`.
- Tests: 46 feature tests in temporary git repositories with real runner captures; full unit suite green.

<!-- finalize:spec-feature:2026-10-12:a6abad0a -->

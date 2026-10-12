# Changelog - 082-conventions-gate-signal

## 2026-10-10 — [Spec]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-008 (all defined)
- **Author:** Claude Code native spec-specify (claude-opus-5-5)
- Read [spec](spec.md): three stories, seven FR, eight AC, Framework Evidence table, Gherkin/Mermaid and QE section.
- Independent native spec review complete and ready after two corrective rounds (feature-scope wording, framework evidence table, write flag instead of subcommand, baseline integrity edge cases); 18/18 requirements covered, 0 blocking findings.
- Clarify inventory not blocking (2 non-critical technical choices carried to the plan); plan progression READY.
- Feature number 082 assigned by the coordinator (081 and 083 are reserved by parallel worktrees).

<!-- finalize:spec-specify:2026-10-10:e39214b3 -->

## 2026-10-10 — [Plan]: Technical plan generated

- **Type:** Feature
- **Spec modified:** No requirement changes; lifecycle status Planned
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation); AC-001 through AC-008 planned
- **Author:** Claude Code native spec-plan (claude-opus-5-5)
- Read [plan](plan.md): six implementation steps, one sequence diagram and one state diagram with paired Gherkin, constitution check, thirteen design decisions and risk-to-evidence mapping.

<!-- finalize:spec-plan:2026-10-10:a5ebf692 -->

## 2026-10-11 — [Feature]: Conventions gate signal implemented

- **Type:** Feature
- **Spec modified:** No requirement changes; lifecycle status Implemented
- **Code modified:** validator/conventions_gates.py, validator/conventions_gate.py, validator/conventions_linter_runner.py, validator/conventions_gate_types.py, validator/conventions_ast/ars_rules.py, validator/conventions_ast/ars_applicability.py (new), validator/conventions_ast/ars_grouping.py (new), validator/conventions_baseline.py (new), validator/conventions_baseline_apply.py (new), validator/conventions_receipt.py, validator/conventions_diffguard.py, validator/cli_commands/conventions_cmd.py, tests/test_conventions_gate_signal.py (new), tests/test_conventions_baseline.py (new), tests/test_conventions_ars_rules.py, Swift AST fixtures, system/conventions-enforcement.md, .specs/conventions/baseline.json (new)
- **AC impacted:** AC-001 through AC-008 certified by the runner-owned execution receipt (84 reviewed assertion bindings)
- **Author:** Claude Code native spec-implement (claude-opus-5-5, --mono)
- LiveSpec repo scope: 1186 errors (849 detector fixtures) before; 282 errors (0 fixtures, 3 grouped ARS) after; 282 recorded in the baseline; `verify --feature repo` PASS with a verified receipt; a temporary new error turns it FAIL listing only that error. 073 and 082 feature scope PASS (0 errors). Repo scan ~20 s → ~7 s.
- Unit suite: 3911 passed / 109 failed / 27 skipped, no new failure versus the main 457a252 reference run in the same environment (3866 / 112 / 27); integration 3a 89 passed.

<!-- finalize:spec-implement:2026-10-11:41daaa07 -->

## 2026-10-12 — [Bugfix]: nested worktrees excluded from the source scan

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/conventions_gates.py, validator/conventions_gate.py, validator/conventions_linter_runner.py, tests/test_conventions_gate_signal.py
- **AC impacted:** None (source collection boundary, same spirit as FR-001 fixture exclusion)
- **Author:** Claude Code (integrator)
- On the main checkout, repo scope walked `.claude/worktrees/*` agent checkouts (~28k extra violations). `.claude/worktrees/**`, `.worktrees/**` and any nested directory holding a `.git` entry are now never sources; repo scope is PASS against the unchanged baseline (280 recorded, 0 new).

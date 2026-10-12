# Changelog - 081-lightweight-outcome-goals

## 2026-10-12 — [Refactor]: Conventions limits after integration on main

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_lightweight_goals.py, tests/lightweight_goals_support.py (new); acceptance-mapping.json spans and source hash rebound to the unchanged assertions
- **AC impacted:** AC-005 (test body only; assertions unchanged)
- **Author:** Claude Code (integrator)
- Against the 082 repo baseline, `test_drifted_contract_recompiles_in_place_and_keeps_valid_evidence` exceeded the 60-line function limit; its saved-goal setup and fact summary moved to a support module. Typed the JSON goal helpers and the stubbed subprocess result so `mypy .` reports no new error versus main 457a252. The independent acceptance review receipt lives in the disposable `.reviews/` cache and must be regenerated before any re-certification.

## 2026-10-10 — [Feature]: Lightweight outcome-based goals

- **Type:** Feature
- **Spec modified:** Yes (new outcome-based goal contract: stop condition, goal scope, recoverable contracts, bounded retries, single conventions gate, deadline, short prompts)
- **Code modified:** validator/goal_outcome.py, goal_recompile.py, goal_canonical.py, goal_payload.py, goal_tasks.py, goal_proof.py, goal_render.py, goal_cli_actions.py, goal_cli_inputs.py, goal_compile.py, goal_pairing.py, goal_generic_evidence.py, goal_task_rules.py, goal_receipt_evidence.py, evidence_policy.py, init_from_code.py; deleted goal_conventions.py and init_goal_conventions.py; 20 skills, system docs, README
- **AC impacted:** AC-001 through AC-009
- **Author:** Claude Code (lead-authorized subagent run; goal proven through the CLI contract)
- Required tasks per contract drop from 25–62 to 2–9; goal step kept in 8 autonomous-capable skills; spec, plan and acceptance-mapping reviews produced by independent reviewer agents and ingested complete/ready.

<!-- finalize:spec-feature:2026-10-10:2db73a41 -->

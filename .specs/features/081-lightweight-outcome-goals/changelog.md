# Changelog - 081-lightweight-outcome-goals

## 2026-10-12 — [Bugfix]: Inline evidence and init deadline test pass on Python 3.12

- **Type:** Bugfix (PR #36 CI)
- **Spec modified:** No
- **Code modified:** `validator/goal_cli_inputs.py` (`--evidence` path probe tolerates ENAMETOOLONG), `tests/test_goal_cli_inputs.py` (new), `tests/test_lightweight_goals.py` (real `ObservedProfile` instead of an empty `object.__new__`)
- **Cause:** CI runs Python 3.12, where `Path(<long inline JSON>).exists()` raises `File name too long` (3.14 returns False), so `goal prove --evidence '<json>'` failed; the deadline test compared a field-less dataclass instance, which only 3.13+ short-circuits on identity.
- **Proof:** unit suite 3840 passed under a Python 3.12 venv with `GITHUB_ACTIONS=true CI=true` and without `AIRESOURCES`, and under the local 3.14 venv; the new evidence test fails without the fix on 3.12.
- **Author:** spec-fix (claude-code)

## 2026-10-12 — [Bugfix]: A missing feature target can no longer satisfy the stop condition

- **Type:** Bugfix (PR #36 review)
- **Spec modified:** No
- **Code modified:** `validator/cli.py` (`validate <path>` exits 2 when the explicit path does not exist), `tests/_goal_contracts_04.py`, `tests/test_goal_contracts.py`, `tests/test_cli.py`
- **Cause:** `livespec validate .specs/features/<slug>` collected no file for a nonexistent path and exited 0, so an unrelated in-project artifact could certify `outcome.verified` for a feature that was never created.
- **Proof:** new tests fail without the fix and pass with it (missing-target CLI exit 2; outcome proof rejected for a missing feature); the passing-outcome test now creates its feature directory.
- **Author:** spec-fix (claude-code)

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

## 2026-10-12 — [Bugfix]: Stop conditions use the caller validator package instead of a consumer-local shadow

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** tests/test_goal_outcome_runtime.py, validator/goal_outcome.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_goal_outcome_runtime.py::test_stop_condition_rejects_consumer_validator_shadow[init-from-code], tests/test_goal_outcome_runtime.py::test_stop_condition_rejects_consumer_validator_shadow[validate]
- **RED receipt:** `.specs/.execution/ecdd63efc0304b2db2865cf69ef8cddd/receipt.json`
- **GREEN receipt:** `.specs/.execution/8cc6c57f4f854191baa743e989f7f3bf/receipt.json`
<!-- bugfix:8cc6c57f4f854191baa743e989f7f3bf -->

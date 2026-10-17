# Implementation Progress — Lightweight Outcome-Based Goals

Read the [approved plan](plan.md) and [implementation map](implementation.md).

| Step | Checkpoint | Status | Observed basis |
|---|---|---|---|
| 1 | Outcome policy module | Done | `goal_requirement`, `stop_condition`, outcome/conventions tasks, stop-condition runner and independent outcome validation. |
| 2 | Contract 3.0 compilation | Done | Required tasks filtered after evidence classification; conventions payload, expectation prose and per-task convention proofs removed; checklist kept. |
| 3 | Proof, retries and recompilation | Done | Three-rejection handback, `goal status` blocked count, in-place recompilation with evidence carry-over, state reuse on re-render, slug resolution for every command. |
| 4 | Deadline | Done | Post-completion deadline check removed from autonomous init. |
| 5 | Prompts and docs | Done | Anti-drift §5 rewritten; STEP 0 short goal step in 8 skills, removed from 12; inventory rows, spec-feature Verify, expectations reference, README, spec-system updated. |
| 6 | Tests and dead code | Done | `tests/test_lightweight_goals.py`; goal tests adapted; child-goal and per-task convention code deleted. |
| Bugfix | Caller runtime import priority | Done | `python -P` excludes consumer cwd from module lookup; real `validate` and `init-from-code --verify-only` subprocess regressions reject a consumer-local validator returning exit 0. |
| Bugfix | Specify review opt-out | Done | Read [regressions](../../../tests/test_specify_review_goal.py): runner-owned RED (7 failures) then GREEN (14 passes), closing bugfix gate ELIGIBLE (5 files / 252 lines), independent native review PASS, conventions feature/repo PASS. Default spec review and semantic progression remain guarded. |

## Goal Lock of this run

Lead-authorized deviation: this run was executed by a subagent that cannot invoke the `/goal` slash command, which is precisely the defect fixed here. Completion is proven with the CLI contract (`livespec goal render/prove/status/archive`) compiled by the new code; no other gate was bypassed. Phase sub-agents were not spawned for specify/plan/implement/test; the supervisor executed them directly, while spec, plan and acceptance-mapping reviews were produced by independent reviewer agents and ingested through `livespec validate --ingest-review` / `livespec test --ingest-mapping-review`.

## Before / after (repository skills, `--auto --model=claude-opus-5-5`)

| Metric | Before (main 457a252) | After |
|---|---|---|
| Required tasks per contract (12 commands) | 25–62 (total 520) | 2–9 (total 59) |
| Contract file, spec-feature | 175 KB (~44k tokens) | 53 KB (~13k tokens) |
| Skills with a goal step | 20 | 8 (autonomous-capable only) |
| STEP 0 text, all skills | 50.2k chars (~12.5k tokens) | 12.0k chars (~3.0k tokens) |
| Anti-drift block (read by every command) | 22.4k chars (~5.6k tokens) | 19.4k chars (~4.9k tokens) |
| `stop`/`BLOCKED` occurrences in skills | 443 | 328 |
| Goal modules (`validator/goal_*.py` + `init_goal_conventions.py`) | 5 813 lines (goal_* only: 5 729) | 5 610 lines (−203 vs 5 813, −119 vs 5 729; ~700 old lines removed, ~490 added in 3 new modules) |

## Gates executed

- Spec review: three independent rounds; round 1 ready, round 2 not ready (critical AC-003 ambiguity: auto-flag scope), round 3 complete/ready after narrowing AC-003 and the code to the autonomous-capable commands.
- Plan review: round 1 not ready (AC-003 ambiguity, unplanned edge cases, `goal_cli_actions.py` over 300 lines), fixed; rounds 2–3 complete/ready.
- Clarify (`--progression plan`) READY; Analyze (`--pre-impl`) exit 0, no CRITICAL/HIGH; preflight: one warning (no project `.venv`, system Python used).
- Acceptance mapping review: rounds 1–2 partial (weak assertions for AC-001/002/006/009), tests strengthened; later rounds ready.
- Read-only Codex audit (16 findings: 2 blocker, 10 major): fixed feature-scope fallback, silent stale recompile, archive recompile notice, recompiled-pair state adoption, canonical handback line, native-goal update rule, conditional `--model`, spec-init `--dry-run` scope, preflight verification wording, restored global Before-DONE checks, `is_file` artifacts, timeout override note, README link. Declined: removing the whole-block `MUST` ban (AC-009 keeps it; no rule was dropped, only rephrased) and the slug branch change (existing-owner commands keep failing closed by design, 078).
- Spec, plan and mapping reviews re-run after the audit fixes (round 5): all complete/ready.
- The first archive drifted: spec-feature expectations require a conventions receipt that its contract never asked for. Fix: `conventions.gate` is now derived from each command's own expectations (spec-feature, implement, test, fix, ship). The running goal recompiled itself in place (`cabfaea0` → `748e7219`), carried 5 proofs, reset the stale execution receipt and outcome, which were proven again.
- Final goal: `livespec goal status` complete 9/9; archive `.specs/.runs/spec-feature-2026-10-10T19-56-53.842811-748e7219-policy2.json` outcome success; `livespec verify-output spec-feature --run <artifact>` success. Execution captured by `livespec test --execution-command ... --report-adapter junit`.
- CLI used as `python3 -m validator.cli` from this worktree: the global `livespec` entry point imports the main checkout.

## Verification (commit 48bb3e6)

- `ruff check .`, `ruff format --check .`, `pyright validator`: clean (mypy: only pre-existing missing-stub/SDK import errors).
- Unit suite: 107 failed / 3850 passed / 29 skipped; the 107 failures are exactly the main 457a252 baseline set in this environment (no new failure).
- Integration level 3A: 89 passed, 1 skipped.

## Review findings carried forward (non-blocking)

- Recompilation is recorded in the state (`recompiled_from`) and the prove output, not in the archive receipt.
- Contracts compiled before this feature (schema 2.0 or older evidence policy) are never migrated.
- Child archives are verified by the parent skill's Supervisor Verify phase (`livespec verify-output`), not by a task of the parent contract.
- A silent stop condition accepts any existing in-project artifact; the exit code remains the real safeguard.
- Constitution principle 5's CLI subcommand list predates `goal`/`verify-output`.

# Implementation: Review Led Delivery

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.agent-sync/skills/spec-*/SKILL.md`, `.agent-sync/agents/livespec-*/prompt.md`, `system/review-led-delivery.md` | FR-001 | Implemented, independently reviewed | 2026-11-13 |
| FR-002 | `validator/goal_payload.py`, retained certification.md files | FR-002 | Two compatibility tests pass | 2026-11-13 |
| FR-003 | `.agent-sync/rules/livespec/`, five system entry points, README | FR-003 | Independently reviewed | 2026-11-13 |
| FR-004 | `docs/review-led-migration.md` | FR-004 | Plan reviewed; installed pair selected and reloaded in Atlas | 2026-11-13 |

## Acceptance Criteria Mapping

| AC | Test File / Observation | Status |
|---|---|---|
| AC-001 | Short skill/policy inspection and final independent review | Reviewed |
| AC-002 | Explicit failure and missing-observation rules in shared policy | Installed Penflow check retains a real comparison FAIL and missing runtime observations |
| AC-003 | Four native role prompt inspection and independent final review | Reviewed |
| AC-004 | `tests/test_review_led_delivery_diagnostics.py` | 2 passed in0.30s |
| AC-005 | Official isolated provider projection from local source | 24 isolated entry points inspected;20 live project skills and4global bootstrap links verified |
| AC-006 | Migration plan | Atlas safe checkpoint, supported upgrade and policy reload observed |

## Files Created/Modified

Twelve compact skills, four role prompts,16 original public archives, routing, system introductions, README, migration plan, goal compiler, regression tests and this feature's documents. No private historical specification or unrelated private commit is published.

## Verification

Ruff check/format pass on changed Python files. Public-port independent review: no material finding. Public PR56 merged to main after Unit, Integration3A, Vitest observer, five visual-target and CodeQL checks passed. The full local public attempt timed out and is not presented as green. Consumer adaptation retains its newer runtime/SDK fixes;27targeted LiveSpec checks and2013Penflow tests pass (2skipped). Installed pair: bound interpreter, no workspace writes, actual comparison FAIL retained. Atlas confirmed a safe checkpoint, selected the pair through the supported command, reloaded the new skills, retained mission history and resumed a real one-line font-source correction without the former certification chain. Product feature A1 remains open until its real rendered/native checks and review; this tool feature does not certify that product.

## Exact implementation inventory

- Skill: read [spec-check](../../../.agent-sync/skills/spec-check/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-check/certification.md).
- Skill: read [spec-feature](../../../.agent-sync/skills/spec-feature/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-feature/certification.md).
- Skill: read [spec-fix](../../../.agent-sync/skills/spec-fix/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-fix/certification.md).
- Skill: read [spec-implement](../../../.agent-sync/skills/spec-implement/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-implement/certification.md).
- Skill: read [spec-plan](../../../.agent-sync/skills/spec-plan/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-plan/certification.md).
- Skill: read [spec-preflight](../../../.agent-sync/skills/spec-preflight/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-preflight/certification.md).
- Skill: read [spec-refine](../../../.agent-sync/skills/spec-refine/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-refine/certification.md).
- Skill: read [spec-ship](../../../.agent-sync/skills/spec-ship/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-ship/certification.md).
- Skill: read [spec-specify](../../../.agent-sync/skills/spec-specify/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-specify/certification.md).
- Skill: read [spec-test](../../../.agent-sync/skills/spec-test/SKILL.md) and its [retained diagnostic](../../../.agent-sync/skills/spec-test/certification.md).
- Role: read [livespec-documenter](../../../.agent-sync/agents/livespec-documenter/prompt.md) and its [retained diagnostic](../../../.agent-sync/agents/livespec-documenter/certification.md).
- Role: read [livespec-implementer](../../../.agent-sync/agents/livespec-implementer/prompt.md) and its [retained diagnostic](../../../.agent-sync/agents/livespec-implementer/certification.md).
- Role: read [livespec-supervisor](../../../.agent-sync/agents/livespec-supervisor/prompt.md) and its [retained diagnostic](../../../.agent-sync/agents/livespec-supervisor/certification.md).
- Role: read [livespec-verifier](../../../.agent-sync/agents/livespec-verifier/prompt.md) and its [retained diagnostic](../../../.agent-sync/agents/livespec-verifier/certification.md).

Read [FR-001 and FR-003 policy](../../../system/review-led-delivery.md), [FR-002 selector](../../../validator/goal_payload.py), [FR-004 migration](../../../docs/review-led-migration.md), and [diagnostic regression tests](../../../tests/test_review_led_delivery_diagnostics.py). Their @spec comments identify the corresponding FR anchor. Read the [progress checkpoints](progress.md) for delivery observations.

The default [Git hook](../../../validator/hooks/pre-commit-hook) is advisory; its [original certification template](../../../validator/hooks/pre-commit-certification-hook) remains unchanged. Read the [hook regression](../../../tests/test_review_led_hook.py) for proof that a commit no longer starts an automatic certification command.

## Bootstrap follow-up

Read [initialization](../../../.agent-sync/skills/spec-init/SKILL.md) and [migration](../../../.agent-sync/skills/spec-migrate/SKILL.md), with their linked operational references. Their original public bodies remain byte-for-byte diagnostic archives. Only this bootstrap delta is retained from the canceled old objective; no new mission states, unlimited-restart dependency or supervisor application is included. Existing Atlas pins and services are unchanged.

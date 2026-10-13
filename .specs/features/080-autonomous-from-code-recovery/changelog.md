# Changelog - 080-autonomous-from-code-recovery

## 2026-10-12 — [Bugfix]: Unsupported manifests recorded, missing package manager warns (FR-001 decision)

- **Type:** Bugfix + Spec Update
- **Spec modified:** Yes (sections: FR-001, new AC-007, Story 1 scenario and flowchart, Key Entities, Edge Cases, Clarifications; status Planned -> In Progress to match the registry)
- **Code modified:** validator/init_profile.py, validator/init_documents.py, validator/init_from_code.py, tests/test_init_profile.py, tests/test_init_documents.py, tests/test_init_recovery.py; plan.md (FR-001 design, tests, AIRESOURCES order)
- **AC impacted:** AC-001, AC-002, AC-003, AC-007
- **Author:** claude-code (spec-fix closure, user decision)

User decision recorded: an unsupported manifest (`go.mod`, `Gemfile`, `pom.xml`…) beside supported ones is recorded as unsupported/unknown in the profile and report and bootstrap continues; a `package.json` without any manager evidence warns explicitly and never fails. Supported ecosystems are listed in FR-001 as implemented. Fresh independent spec and plan reviews are ready and the implement gate returns READY, closing the pending EPERM/hermetic-tests spec-fix.

## 2026-10-12 — [Refactor]: Init goal profile aliases reduced to one case per profile

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_init_goal_profiles.py
- **AC impacted:** AC-006 (coverage unchanged)
- **Author:** claude-code (test-suite cleanup lot 3)

Alias permutations that reach the same profile branch were dropped (19 -> 13 cases); the `-d` alias stays where it has its own verify branch. One prose assertion was removed.

## 2026-10-09 — [Spec]: Feature specification created

- **Type:** Spec Update

- **Spec modified:** Yes (new evidence-based autonomous bootstrap and recovery contract; canonical AC headings; existing flag semantics)
- **Code modified:** None in this phase
- **AC impacted:** AC-001 through AC-006
- **Author:** Codex native spec-specify
- Read [spec](spec.md), including two P1 stories, four FR, six AC, Gherkin/Mermaid and quality gates.
- Native gpt-6.1-sol spec review is complete/ready at 60000 characters per submission; thirteen obligations covered. Six baseline context warnings retained; two blocking context findings resolved by the corrective normative contract, not by an implementation claim.
- Current Clarify inventory is empty and plan progression is READY; fixture execution and backend correction remain later phases.

<!-- finalize:spec-specify:2026-10-09:2dbaa83d -->

### 2026-10-09 — Technical plan generated for evidence-based autonomous bootstrap and safe recovery.

- **Type:** Feature
- **Spec modified:** No requirement changes; lifecycle status Planned
- **Code modified:** None (plan.md created)
- **AC impacted:** AC-001 through AC-006 planned; execution remains later
- **Author:** Codex native spec-plan
- Read [plan](plan.md): six implementation steps, one sequence diagram and one state diagram with paired Gherkin, explicit constitution check and risk-to-evidence mapping.

<!-- finalize:spec-plan:2026-10-09:1bde99f4 -->

### 2026-10-09 — Technical plan generated for evidence-based autonomous bootstrap and safe recovery.

- **Type:** Feature
- **Spec modified:** No requirement changes; lifecycle status Planned
- **Code modified:** None (plan.md created)
- **AC impacted:** AC-001 through AC-006 planned; execution remains later
- **Author:** Codex native spec-plan
- Read [plan](plan.md): six implementation steps, one sequence diagram and one state diagram with paired Gherkin, explicit constitution check and risk-to-evidence mapping.

<!-- finalize:spec-plan:2026-10-09:ba349e73 -->

### 2026-10-09 — Technical plan generated for evidence-based autonomous bootstrap and safe recovery.

- **Type:** Feature
- **Spec modified:** No requirement changes; lifecycle status Planned
- **Code modified:** None (plan.md created)
- **AC impacted:** AC-001 through AC-006 planned; execution remains later
- **Author:** Codex native spec-plan
- Read [plan](plan.md): six implementation steps, one sequence diagram and one state diagram with paired Gherkin, explicit constitution check and risk-to-evidence mapping.
- **Current structural repair:** Required plan frontmatter and Summary heading added without changing the technical design or spec requirements; structural validation reports 0 errors, 0 warnings, score 100.

<!-- finalize:spec-plan:2026-10-09:bcaf92c9 -->

## 2026-10-09 — Bugfix: deliver observed bootstrap recovery

- **Type:** Bugfix
- **Spec modified:** Yes; explicit AIRESOURCES routing and shipping identifier 080 avoid a collision with existing feature 079.
- **Code modified:** observed profile/documents/probes/recovery/verification, init goal conventions and branches, installer/sync and canonical init skill.
- **AC impacted:** AC-001 through AC-006.
- Read [implementation](implementation.md) for fixture checks and operational limits. Final feature/repo certification remains incomplete; successful Handy init is distinct operational evidence.

### 2026-10-12 — Fix: zombie-group EPERM, deterministic budgets and hermetic init tests

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `validator/init_probes.py`, `tests/init_clock_support.py` (new), `tests/test_init_probes.py`, `tests/test_init_hook_pipeline.py`, `tests/test_init_recovery.py`, `tests/test_spec_init_autonomous_bootstrap.py`
- **Gaps closed:** FR-002/AC-003 — `killpg` EPERM on macOS zombie-only groups escaped as PermissionError; budget tests depended on machine load; init tests depended on a sibling `../ai-ressources` checkout.
- **Remaining:** readiness gate BLOCKED — the claude-opus-5-5 spec review marks FR-001 ambiguous (supported manifest ecosystems); business decision pending.
- **Author:** spec-fix (claude-opus-5-5)

<!-- finalize:spec-fix:2026-10-12:7710d267 -->

## 2026-10-13 — [Bugfix]: Fresh bootstrap passes validation, definition of done and archive

- **Type:** Bug Fix
- **Spec modified:** Yes (FR-005, AC-008, SC-004, Story 1 scenario, Clarifications)
- **Code modified:** `scripts/init.sh`, `validator/init_documents.py`, `validator/init_recovery.py`, `validator/init_from_code.py`, `validator/penflow_contract.py`, `validator/cli_commands/penflow_contract_cmd.py`, `.agent-sync/skills/spec-init/SKILL.md`, `README.md`, `tests/test_init_bootstrap_closure.py` (new)
- **Gaps closed:** `livespec validate` errors on `changelog.md`, `preflight.md` and `stacks/_default.md`; missing `.specs/design/`, ignore patterns and command list (installer output overwritten by the backend); first `goal archive` drift (`Penflow contract` marker, transcript protocol); Quick Start prerequisites.
- **Remaining:** formal readiness/certification as for FR-001…FR-004.
- **Author:** spec-fix (claude-opus-5-5)

## 2026-10-13 — [Feature]: Migration v23 repairs earlier bootstraps

- **Type:** Feature
- **Spec modified:** Yes (FR-006, AC-009, SC-005, Story 1 scenario, Clarifications)
- **Code modified:** `validator/init_bootstrap_repair.py` (new), `scripts/migrate-init-bootstrap-repair.sh` (new), `migrations/23/migrate.md` (new), `VERSION`, `.specs/livespec-version`, `tests/test_init_bootstrap_migration.py` (new)
- **AC impacted:** AC-009
- **Author:** spec-fix (claude-opus-5-5)

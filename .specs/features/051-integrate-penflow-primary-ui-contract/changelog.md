# Changelog — 051-integrate-penflow-primary-ui-contract

## 2026-05-26 — [Check]: Single Penflow source contract verified with real Brainstorm import

- **Type:** Check
- **Spec modified:** No
- **Code modified:** None
- **Check report:** `checks/2026-05-26.md`
- **AC impacted:** AC-011, AC-012, AC-013
- **Author:** codex

## 2026-05-26 — [Bugfix]: Single Penflow source contract enforced

- **Type:** Bugfix
- **Spec modified:** Yes (AC-011..AC-013, FR-010..FR-012)
- **Code modified:** `validator/penflow_contract.py`, `validator/cli_commands/penflow_contract_cmd.py`, `validator/cli_commands/design_alignment_cmd.py`, `validator/goal_contracts.py`, `scripts/migrate-visual-tests.js`
- **Docs modified:** `.agent-sync/skills/spec-init/SKILL.md`, `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-feature/expectations.md`, `.agent-sync/skills/spec-test/expectations.md`, `.specs/spec-system.md`, `system/spec-system.md`, `system/testing/penflow-contract.md`, `system/testing/design-alignment.md`, `system/testing/design-alignment-quality.md`, `system/schemas/design-alignment-manifest.md`, `README.md`
- **AC impacted:** AC-011, AC-012, AC-013
- **Author:** codex

## 2026-05-21 — [Spec]: Feature created

- **Type:** Spec
- **Spec modified:** Yes
- **Code modified:** None yet
- **AC impacted:** AC-001..AC-009
- **Author:** codex

## 2026-05-21 — [Feature]: Penflow primary UI contract integrated

- **Type:** Feature
- **Spec modified:** Yes (implementation mapping)
- **Code modified:** `validator/penflow_contract.py`, `validator/cli_commands/penflow_contract_cmd.py`, `validator/cli_commands/__init__.py`
- **Docs modified:** `.agent-sync/skills/spec-init/SKILL.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-plan/SKILL.md`, `.agent-sync/skills/spec-implement/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-check/SKILL.md`, `system/testing/penflow-contract.md`, `README.md`
- **AC impacted:** AC-001..AC-009
- **Author:** codex

## 2026-05-21 — [Bugfix]: Penflow actual-tree absence classified explicitly

- **Type:** Bugfix
- **Spec modified:** Yes (AC-010, FR-009, implementation mapping)
- **Code modified:** `validator/penflow_contract.py`, `validator/cli_commands/penflow_contract_cmd.py`, `tests/test_penflow_contract.py`, `tests/test_penflow_contract_command_contract.py`
- **Docs modified:** `.agent-sync/skills/spec-init/expectations.md`, `.agent-sync/skills/spec-specify/expectations.md`, `.agent-sync/skills/spec-plan/expectations.md`, `.agent-sync/skills/spec-implement/expectations.md`, `.agent-sync/skills/spec-test/expectations.md`, `.agent-sync/skills/spec-check/expectations.md`, `.agent-sync/skills/spec-init/SKILL.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-plan/SKILL.md`, `.agent-sync/skills/spec-implement/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-check/SKILL.md`, `system/testing/penflow-contract.md`
- **AC impacted:** AC-006, AC-007, AC-010
- **Author:** codex

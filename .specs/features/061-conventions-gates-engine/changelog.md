# Changelog - 061-conventions-gates-engine

## 2026-06-12 — [Refactor]: Remove delegate_to from schema v1

- **Type:** Refactor
- **Spec modified:** Yes (AC-013, AC-016, FR-007)
- **Code modified:** validator/conventions_gates.py, validator/conventions_gate.py, validator/conventions_delegate.py (deleted), tests/test_conventions_gates_schema.py, tests/test_conventions_verify.py
- **AC impacted:** AC-013, AC-016
- **Author:** spec-fix worker (Codex)

## 2026-06-12 — [Bugfix]: Critic cycle 4 id-spoof and read-error hardening

- **Type:** Bugfix
- **Spec modified:** Yes (AC-016, AC-017)
- **Code modified:** validator/conventions_delegate.py, validator/conventions_gate.py, tests/test_conventions_verify.py
- **AC impacted:** AC-016, AC-017
- **Author:** spec-fix worker (Codex)

## 2026-06-12 — [Bugfix]: Critic cycle 3 hardening

- **Type:** Bugfix
- **Spec modified:** Yes (AC-013 wording, AC-015)
- **Code modified:** validator/conventions_delegate.py, validator/conventions_gate.py, tests/test_conventions_verify.py
- **AC impacted:** AC-013, AC-015
- **Author:** spec-fix worker (Codex)

## 2026-06-12 — [Bugfix]: Critic P0/P1 hardening

- **Type:** Bugfix
- **Spec modified:** Yes (AC-011 through AC-014, FR-007)
- **Code modified:** validator/conventions_gate.py, validator/conventions_linter.py, validator/conventions_delegate.py, validator/conventions_receipt.py, tests/test_conventions_verify.py, tests/test_conventions_receipt.py, .gitignore
- **AC impacted:** AC-011 through AC-014
- **Author:** spec-fix worker (Codex)

## 2026-06-12 — [Spec]: Conventions Gates Engine specified

- **Spec modified:** Yes (created)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-010
- **Author:** spec-feature worker (Codex)

## 2026-06-12 — [Plan]: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec-feature worker (Codex)

## 2026-06-12 — [Feature]: Initial conventions gates engine

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** validator/conventions_gates.py, validator/conventions_gate.py, validator/conventions_report.py, validator/conventions_receipt.py, validator/conventions_lang/*, validator/cli_commands/utility_cmd.py, tests/test_conventions_*.py, .specs/conventions-gates.yaml
- **AC impacted:** AC-001 through AC-010
- **Author:** spec-implement worker (Codex)

### 2026-06-12 — Feature: Initial conventions gates engine

- **Type:** Feature
- **Spec modified:** Yes (061 artifacts created)
- **Code modified:** validator/conventions_gates.py, validator/conventions_gate.py, validator/conventions_report.py, validator/conventions_receipt.py, validator/conventions_lang/*, validator/cli_commands/utility_cmd.py, tests/test_conventions_*.py, .specs/conventions-gates.yaml
- **AC impacted:** AC-001 through AC-010
- **Author:** spec-feature worker (Codex)

<!-- finalize:spec-feature:2026-06-12:a140dc75 -->

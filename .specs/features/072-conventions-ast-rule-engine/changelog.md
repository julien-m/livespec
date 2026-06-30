# Changelog — 072-conventions-ast-rule-engine

### 2026-06-29 — [Spec Update]: Superseded default-mode rollout by 073

- **Type:** Spec Update
- **Spec modified:** Yes
- **Code modified:** None
- **AC impacted:** AC-001, AC-002, SC-001, SC-002
- **Author:** codex
- **Reason:** Feature 073 makes AST `enforce` the default and keeps `off`/`observe` as opt-in modes.

### 2026-06-29 — [Bugfix]: Correct AC-014 implementation map paths

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** AC-014
- **Author:** codex
- **Verification:** `livespec doctor --format json`

### 2026-06-29 — Check: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** 35/35 verified (100%), 0 partial, 0 missing; 10 non-blocking convention warnings
- **Report:** `checks/2026-06-29.md`
- **Author:** codex

## 2026-06-29 — [Test]: 100% AC covered

- **Type:** Test
- **Spec modified:** No
- **Code modified:** No new tests generated during `spec-test`; existing targeted tests were executed.
- **Coverage:** 17/17 AC covered (100%)
- **Report:** `checks/2026-06-29-test.md`
- **Author:** codex

## 2026-06-29 — [Feature]: Implemented Conventions AST Rule Engine

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** Yes
- **AC impacted:** AC-001 through AC-017
- **Author:** codex
- **Verification:** `ruff check` targeted scope; `pytest` targeted scope — 177 passed; conventions receipt `.specs/conventions/runs/implement-final-001/receipt.json` PASS.

<!-- finalize:spec-implement:2026-06-29:58f6d072 -->
<!-- finalize:spec-implement:2026-06-29:7d37e57a -->

## 2026-06-29 — Feature: Add technical plan

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** codex

## 2026-06-29 — Spec Update: Add functional specification

- **Type:** Spec Update
- **Spec modified:** Yes (initial feature specification)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-017
- **Author:** ai-agent

<!-- finalize:spec-specify:2026-06-29:4d481d61 -->

<!-- finalize:spec-plan:2026-06-29:fdbed7ea -->

### 2026-06-29 — [Feature]: Completed Conventions AST Rule Engine pipeline

- End-to-end spec-feature pipeline completed through implement, test, audit, full pytest, Ruff, conventions receipt, and .specs validation.

<!-- finalize:spec-feature:2026-06-29:3ef3e24f -->

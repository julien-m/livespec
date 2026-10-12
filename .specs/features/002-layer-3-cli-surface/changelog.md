# Changelog — 002-layer-3-cli-surface

> Per-feature changelog for Layer 3 CLI Surface.
> Global changes are tracked in `.specs/changelog.md`.

## 2026-10-12 — [Refactor]: Replace tautological SdkTestRunner tests

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_sdk_test_runner.py
- **AC impacted:** AC-007 (budget env, unchanged test)
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** `test_without_budget` compared a value with itself; it now asserts the variable is absent without a budget, and a new case asserts an inherited budget is preserved. Removed `test_total_equals_sum`, which checked a field the test had just set.

---

## 2026-04-13 — [Fix]: Added missing @spec anchors

- **Type:** Fix
- **Scope:** Feature 002
- **Description:** Added 3 missing `@spec` anchors (FR-006, FR-007, FR-009) and normalized all existing anchors to single-line convention with full spec path fragments. 9/9 FR now have anchors — 100% anchor alignment.
- **Author:** spec.fix

---

## 2026-04-13 — [Check]: Spec-code alignment verified

- **Type:** Check
- **Scope:** Feature 002
- **Description:** spec.check verified 100% functional alignment (9/9 FR, 10/10 AC). 3 @spec anchors missing (FR-006, FR-007, FR-009). Existing anchors lack full spec path fragments.
- **Author:** spec.check

---

## 2026-04-13 — [Plan]: Plan created

- **Type:** Plan
- **Scope:** Feature 002
- **Description:** Plan created for Layer 3 CLI Surface -- 7 implementation steps, 3 diagrams (sequence, state, flowchart). 1 new file (validator/sdk_test_runner.py), 2 modified (cli.py, exceptions.py), 2 test files.
- **Author:** spec.plan --auto

---

## 2026-04-13 — [Spec]: Spec created

- **Type:** Spec
- **Scope:** Feature 002
- **Description:** Spec created for Layer 3 CLI Surface — 4 stories, 10 AC, 9 FR. Covers `--sdk-isolated` flag wiring to `pytest tests/integration/ -m level_3b`, feature-scoped runs, budget guard forwarding, and JSON output format.
- **Author:** spec.specify --auto

---

## 2026-10-12 — [Refactor]: CLI and SDK specify tests made deterministic

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_cli.py, tests/integration/test_spec_specify.py
- **AC impacted:** None (AC-010 help test kept)
- **Author:** Claude Code (test-suite cleanup, lot 1)
- `--sdk-isolated` tests now resolve `.specs/` from a per-test project instead of the caller's working directory; the `--smart` test asserts the explicit Pass 2 refusal instead of any non-zero exit; help-only tests for validate, install-hook and `--no-review` removed. The opt-in specify test counts distinct AC/FR ids, so legitimate re-references no longer fail the sequence check.

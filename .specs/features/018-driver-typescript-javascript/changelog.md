## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-012 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Plan + Implementation: TS/JS driver shipped

- **Type:** Plan + Implementation
- **Spec modified:** No
- **Code modified:**
  - `livespec/drivers/typescript.yaml` (replaced 016 stub with 4-capability manifest)
  - `validator/drivers/typescript_detector.py` (new)
  - `validator/drivers/stryker_parser.py` (new)
  - `tests/unit/test_typescript_detector.py` (new — 16 tests)
  - `tests/unit/test_stryker_parser.py` (new — 11 tests)
  - `tests/integration/test_driver_typescript.py` (new — 11 tests)
- **AC impacted:** AC-001 through AC-012 (all covered)
- **Verification:** `ruff check .` passes. `mypy .` currently reports pre-existing repository issues outside the Feature 018 file set.
- **Author:** spec.feature (auto)

## 2026-10-12 — [Refactor]: Driver integration tests reduced to real behavior

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_driver_typescript.py, implementation.md
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Kept registry discovery and schema-validated capability set; removed YAML value pins and runner/package-manager cases duplicated by tests/unit/test_typescript_detector.py.

## 2026-10-12 — Spec Update: runner/package-manager detection flagged as unwired

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None (implementation.md statuses only)
- **AC impacted:** AC-002 (Partial)
- **Author:** Claude Code (dead-code resolution)
- `detect_test_runner`, `detect_package_manager` and `has_dependency` have no production caller: `typescript.yaml` hardcodes `npx vitest`/`npx stryker`. Both wiring (per-runner command variants) and removal (rely on `.specs/drivers/typescript.yaml` overrides) are defensible, so the code is kept and the decision is escalated to the user.

## 2026-10-12 — Feature: runner and package-manager detection wired into livespec test

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** livespec/drivers/typescript.yaml, validator/drivers/typescript_detector.py, validator/drivers/placeholders.py, validator/drivers/preconditions.py (new), validator/drivers/runner.py, validator/drivers/test_config.py, tests/integration/test_driver_typescript_flow.py (new), tests/unit/test_typescript_detector.py
- **AC impacted:** AC-002, AC-003, AC-008, AC-009, AC-012 (now enforced in the real flow)
- **Author:** Claude Code (dead-code resolution, user decision)
- The built-in manifest now expands `{js_exec}` (npx / pnpm exec / yarn / bunx, from `packageManager` then lockfiles, including `bun.lock`) and `{js_coverage_args}`/`{js_test_args}` (jest or vitest). Project overrides keep priority. Missing fast-check / Stryker skips with an install hint. `test-config` reports the detected runner and no longer writes `vitest.config.ts` into jest projects. FR-002/FR-004/AC-002 back to Implemented.

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
- **AC impacted:** AC-001 through AC-008 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Implemented

- **Type:** Implementation
- **Spec modified:** No
- **Code modified:**
  - `validator/drivers/test_config.py` (new) — `GeneratedFile`, per-stack generators, `generate_test_config`, `generate_ci_workflow`, `update_conventions_testing_domain`, `materialize_files`, `pick_primary_driver`.
  - `validator/drivers/test_config_cli.py` (new) — `livespec init test-config` Typer app.
  - `validator/cli.py` — wires `init_app`.
  - `validator/drivers/__init__.py` — exports new public surface.
  - `tests/test_drivers_test_config.py` (new) — 43 tests (8 ACs, 4 ECs, CLI integration).
- **AC impacted:** AC-001 through AC-008 (all covered)
- **Tests:** 917 passed (+43 new vs 874 baseline), 28 skipped, 0 failed
- **Author:** spec.feature

## 2026-10-12 — [Refactor]: Prose-pinning contract test replaced by CLI resolution

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_command_conventions_contract.py
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Every `livespec conventions ...` invocation documented in a SKILL.md must resolve to a real subcommand and real options of the shipped Typer app; sentence pins removed.

## 2026-10-12 — [Refactor]: Test suite cleanup (lot 2)

The per-stack generator matrix now uses a non-default 85% threshold, so every stack proves propagation; the two single-stack propagation duplicates and a test of Python's frozen dataclass behaviour were removed. AC-004 mapping updated.

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** `tests/test_drivers_test_config.py`, `implementation.md` (AC-004 row)
- **AC impacted:** AC-001, AC-004 (coverage kept)
- **Author:** Claude Code

# Implementation — 025 Mutation Testing On-Demand

- **Feature:** 025-mutation-testing-on-demand
- **Branch:** feature/025-mutation-testing-on-demand
- **Date:** 2026-05-07
- **Status:** Implemented

## Files Touched

| Path | Change | Purpose |
|---|---|---|
| `validator/drivers/mutation_report.py` | NEW | Dataclasses, normalisers, renderer, writer, orchestration. |
| `validator/drivers/__init__.py` | MODIFIED | Re-export the new public surface. |
| `tests/test_mutation_report.py` | NEW | 15 unit tests covering FRs, ACs, ECs. |
| `commands/test.md` | MODIFIED | Document the `--mutation` flag. |

## Public surface

`from validator.drivers import …`:

- `MutationResult`, `SurvivorRef` — frozen dataclasses (FR-003, FR-004).
- `run_mutation(driver, *, project_root, report_path, timeout, env)` — orchestration entry point (FR-001, AC-001, AC-002, AC-005, AC-007).
- `write_mutation_report(result, report_path)` — historical report writer (FR-002, AC-003, AC-004, EC-002, EC-003).
- `render_report_entry(result, *, max_survivors=20)` — Markdown rendering (EC-002).
- Normalisers: `normalise_mutmut`, `normalise_stryker`, `normalise_pitest`, `normalise_cargo_mutants`, `normalise_muter`.
- `alternative_for(driver_name)` — "use X instead" suggestion when capability is missing.
- `mutation_result_to_dict(result)` — serialisation helper for downstream tooling.

## AC ↔ implementation map

| AC | Status | Where |
|---|---|---|
| AC-001 — `--mutation` invokes the active driver's mutation capability | covered | `run_mutation` calls `run_capability(driver, "mutation", …)`; documented in `commands/test.md`. Standard `/spec.test` runs without the flag and never imports this module. |
| AC-002 — "not implemented" + alternative + exit 0 | covered | `run_mutation` returns `None` when `driver.get_capability("mutation") is None`; `alternative_for("go")` returns "Consider gopter (property-based testing) as a richer alternative". |
| AC-003 — Report file contains date, driver, kill rate, counts, survivors | covered | `render_report_entry` renders all required fields; `write_mutation_report` creates the file with header. |
| AC-004 — Newest entry first, previous entries preserved | covered | `_split_existing_entries` parses existing file; new entry is prepended. |
| AC-005 — Optional `mutation_threshold` triggers a gate | covered | `_apply_threshold(result, driver.mutation.threshold)` sets `gate_failed`. The slash command translates `gate_failed=True` into a non-zero exit code. |
| AC-006 — Output includes link to full report | covered | Documented in `commands/test.md` ("Full report: .specs/testing/mutation-report.md"). |
| AC-007 — Tool not installed → install hint, exit 0 | covered | `run_capability` returns exit code 127 with "command not found"; `run_mutation` translates this to a `MutationResult` with `note="tool not installed — …"`. |
| EC-001 — Timeout note recorded | covered | `MutationResult.note` carries the timeout marker (used by callers when `subprocess.TimeoutExpired` is surfaced). |
| EC-002 — >100 survivors → top 20 + "more survivors" line | covered | `render_report_entry` truncates to `max_survivors` and emits the trailing notice. |
| EC-003 — `.specs/testing/` created on demand | covered | `write_mutation_report` calls `report_path.parent.mkdir(parents=True, exist_ok=True)`. |
| SC-001 — Standard `/spec.test` does not invoke mutation | covered | `commands/test.md` flag table is the single integration point; the runner module is only imported by the `--mutation` flow. |
| SC-002 — Markdown is human-readable | covered | Rendered output uses headings, dashed lists, and code spans. |
| SC-003 — Historical entries preserved across runs | covered | Writer prepends rather than overwriting (test `test_write_mutation_report_prepends_subsequent_runs`). |

## Driver-specific dispatch

`run_mutation` dispatches on `driver.name`:

- `python` → mutmut stdout → `parse_mutmut_results` → `normalise_mutmut`.
- `typescript` / `javascript` → Stryker JSON file (path from manifest, default `reports/mutation/mutation.json`) → `load_stryker_report` → `normalise_stryker`.
- `jvm` → pitest XML in stdout → `parse_pitest_xml` → `normalise_pitest`.
- `rust` → cargo-mutants JSON → `parse_cargo_mutants_json` → `normalise_cargo_mutants`.
- `swift` → muter stdout regex → `normalise_muter`.
- Any other driver name → returns a result with a "no parser" note (graceful fallback).

The pre-existing `parse_pitest_xml` and `parse_cargo_mutants_json` only return
counts (not survivor refs). Per-survivor extraction for jvm and rust is
deliberately deferred — `normalise_pitest` and `normalise_cargo_mutants`
accept a `survivors` argument for future enrichment without breaking the
public surface.

## Tests

`tests/test_mutation_report.py` — 15 tests, all passing:

- 5 normaliser tests (mutmut / stryker / pitest / cargo-mutants / muter).
- 2 renderer tests (truncation, threshold gate output).
- 3 writer tests (create, prepend, parent dir creation).
- 4 orchestration tests (no capability, install hint, full run with report write, threshold gate).
- 1 helper test (`alternative_for`).

Suite-wide check: `pytest tests/` → **874 passed, 28 skipped** (no regressions).
`pyright validator/` → **117 errors** (pre-existing baseline; new module adds 0).
`ruff check validator/` → **All checks passed**.

## Deviations

None. The plan and the implementation match.

## Follow-ups

- **Per-survivor extraction for jvm/rust.** The current parsers expose counts
  only. A follow-up feature can enrich `parse_pitest_xml` and
  `parse_cargo_mutants_json` to return survivor file/line tuples; the
  `survivors` parameter on the normalisers is the future hook.
- **CLI subcommand.** Today `/spec.test --mutation` is documented as a slash
  command flag handled by the agent; adding a thin `livespec mutation run`
  Typer subcommand that calls `run_mutation` directly would be a small
  ergonomics win.

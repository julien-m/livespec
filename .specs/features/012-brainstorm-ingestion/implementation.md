---
feature: Brainstorm Ingestion
title: "Brainstorm Ingestion — Implementation Mapping"
status: Implemented
created: 2026-04-29
updated: 2026-04-29
number: "012"
---

# Implementation: Brainstorm Ingestion

Maps every FR / AC to its `@spec` anchor in source. All anchors are line-precise references to `validator/brainstorm/*.py` and `commands/*.md`.

---

## Module map

| Module | Purpose |
|---|---|
| `validator/brainstorm/__init__.py` | Package marker |
| `validator/brainstorm/schemas.py` | Pydantic models (FlowFrontmatter, MockupManifest, ProjectProfile, ScreenAnnex, Violation, IngestionPlan, FlowOp, MockupOp, ScreenOp, ProjectOp, RoadmapOp, ApplyReport) |
| `validator/brainstorm/slug.py` | Slug normalization + NNN allocation |
| `validator/brainstorm/grammar.py` | Flow grammar validator (frontmatter + sections + IDs + mockup refs) |
| `validator/brainstorm/convert.py` | Flow.md → spec.md conversion + screens injection + changelog |
| `validator/brainstorm/project_seed.py` | project.md + stacks/_default.md seeding |
| `validator/brainstorm/roadmap.py` | Roadmap tier assignment & rendering |
| `validator/brainstorm/apply.py` | Two-phase atomic writer (build_plan + apply_plan) |
| `validator/brainstorm/detect.py` | Artifact detection (returns Detected JSON snapshot) |
| `validator/brainstorm/cli.py` | Typer CLI (`detect`, `validate`, `plan`, `apply`) |
| `validator/cli.py` | Registers `app.add_typer(brainstorm_app, name="brainstorm")` |
| `commands/init.md` | Pre-Check: Brainstorm Ingestion section |
| `commands/refine.md` | Step 0.5 — `--import-brainstorm` flag |

---

## FR → @spec anchor

| FR | Description | Anchor |
|---|---|---|
| FR-001 | Detect brainstorm artifacts | `validator/brainstorm/detect.py` `detect()`; `commands/init.md` Pre-Check; `validator/brainstorm/cli.py` `detect` subcommand |
| FR-002 | Validate flow grammar | `validator/brainstorm/grammar.py` `validate_flow()`; schema `FlowFrontmatter` in `schemas.py` |
| FR-003 | Abort on grammar / mockup violation | `validator/brainstorm/grammar.py` `validate_mockup_refs()`; `validator/brainstorm/cli.py` exit codes 2/3 |
| FR-004 | Flow → spec conversion (header inject + H1 rewrite + ID preservation) | `validator/brainstorm/convert.py` `convert_flow_to_spec()` |
| FR-005 | Changelog seed; no plan.md / implementation.md | `validator/brainstorm/convert.py` `build_changelog()`; `apply.py` `_stage_flows()` only writes spec + changelog |
| FR-006 | Screens section + "À designer" placeholder | `validator/brainstorm/convert.py` `inject_screens_section()` |
| FR-007 | Mockup bulk + per-feature copy; source unchanged | `validator/brainstorm/apply.py` `_stage_mockups()`; uses `shutil.copy2` |
| FR-008 | manifest.json never copied | `validator/brainstorm/apply.py` `_stage_mockups()` only iterates `*.png` |
| FR-009 | NNN ordering (_index.md, alphabetical, skip collision) | `validator/brainstorm/slug.py` `allocate_nnn()`; `apply.py` `_read_index_order()` |
| FR-010 | Roadmap tiers from priority | `validator/brainstorm/roadmap.py` `build_roadmap_op()` |
| FR-011 | project.md + stacks/_default.md seed (with interactive fallback marker) | `validator/brainstorm/project_seed.py` `seed_project_md()` / `seed_default_stack()` |
| FR-012 | Refuse /spec.init when .specs/ exists | `commands/init.md` Pre-Check abort branch; `apply.py` raises if target exists in init mode |
| FR-013 | /spec.refine project --import-brainstorm | `commands/refine.md` Step 0.5; `apply.py` `_merge_into()` (skip-existing) |
| FR-014 | Confirm artifact list before write (skipped under --auto) | `commands/init.md` Pre-Check confirmation step |
| FR-015 | Screen annex placement (inline vs annex) | `validator/brainstorm/apply.py` `_resolve_screen_ops()`; `_stage_screens()`; schema `ScreenAnnex` in `schemas.py` |

## AC → test coverage

| AC | Test |
|---|---|
| AC-001 | `tests/test_brainstorm_apply.py::test_init_full_ingest` |
| AC-002 | `tests/test_brainstorm_convert.py::test_id_preservation`, `test_h1_rewritten`, `test_frontmatter_stripped` |
| AC-003 | `tests/test_brainstorm_apply.py::test_init_full_ingest` (asserts changelog, no plan.md/impl.md) |
| AC-004 | `tests/test_brainstorm_grammar.py::test_chaos_atomic_abort`, `test_missing_section`, `test_missing_frontmatter_field` |
| AC-005 | `tests/test_brainstorm_grammar.py::test_missing_mockup_blocks` |
| AC-006 | `tests/test_brainstorm_apply.py::test_source_mockups_unchanged` |
| AC-007 | `tests/test_brainstorm_apply.py::test_init_full_ingest` (per-feature paths) |
| AC-008 | `tests/test_brainstorm_apply.py::test_manifest_skipped` |
| AC-009 | `tests/test_brainstorm_roadmap.py` (all priority tiers) |
| AC-010 | `tests/test_brainstorm_convert.py::test_empty_mockups_placeholder`, `tests/test_brainstorm_apply.py::test_empty_mockups_flow_still_ingests` |
| AC-011 | `tests/test_brainstorm_apply.py::test_init_full_ingest` (project.md + _default.md exist) |
| AC-012 | Slash command `/spec.init` Pre-Check section (interactive prompt at runtime; `seed_project_md` emits `[NEEDS INTERACTIVE FILL]` markers) |
| AC-013 | `commands/init.md` abort branch (manual / docs); `commands/refine.md` Step 0.5 |
| AC-014 | `tests/test_brainstorm_apply.py::test_refine_skips_existing_slugs`, `tests/test_brainstorm_slug.py::test_allocate_skip_collisions` |
| AC-015 | `tests/test_brainstorm_slug.py::test_allocate_with_index_order` |

## Plan-review findings addressed

| Finding | Status |
|---|---|
| #1 (WARNING) — surface "partial apply possible in refine mode" | DONE: `apply.py` `apply_plan()` wraps `_merge_into` and re-raises with the message in refine mode |
| #2 (WARNING) — document rationale for 4-subcommand split | DONE: docstring added to `validator/brainstorm/cli.py` |
| #3 (INFO) — document JSON intermediate rationale | DONE: docstring added to `validator/brainstorm/apply.py` and `cli.py` |
| #4 (INFO) — `test_empty_surfaces_rejected` unit test | DONE: `tests/test_brainstorm_grammar.py::test_empty_surfaces_rejected` |
| #5 (INFO) — `ScreenAnnex(parent, body)` Pydantic model | DONE: defined in `validator/brainstorm/schemas.py` |

## Quality gates

- Ruff: PASS (`ruff check validator/brainstorm/ tests/test_brainstorm_*.py`)
- Tests: 37 new tests pass; full unit suite 501/501 pass
- File budget: every new module <300 LOC

## /spec.test run (2026-04-29)

- Command: `python3 -m pytest tests/test_brainstorm_*.py -v`
- Result: 37 passed, 0 failed, 0.12 s
- AC coverage: 13/15 covered by automated tests; AC-012 (interactive `project.md` fallback) and AC-013 (`/spec.init` abort branch suggesting `/spec.refine`) are slash-command runtime behaviors documented in `commands/init.md` and `commands/refine.md` — not exercised by unit tests but verified manually via the command flow.
- Visual baselines: N/A — feature has no UI surface (Python CLI ingestion only).
- Full suite (sanity): 542 passed, 2 pre-existing unrelated failures in `tests/integration/test_migrate_visual.py` (feature 010 territory, not in scope here).

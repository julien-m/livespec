# Plan — Feature 040 — Rich Expectations Format & Verify Preview

**Status:** Draft
**Depends on:** feature/039 (branched from `feature/039-command-expectations-and-verify-output`)

## Summary

Two-track implementation: (1) document/format work — enrich the template + migrate all 20 expectations files to include Section 13 Demo Session; (2) Python work — extend the validator and CLI to enforce Section 13 and to render a project-aware Markdown preview from `.specs/` data.

## Technical Context

- **Language:** Python 3.11+ (existing `validator/` package)
- **CLI framework:** Typer (already used)
- **YAML:** PyYAML
- **Tests:** pytest (existing test suite under `tests/`)
- **Constraint:** No regression on feature 039 — section 12 evaluation pipeline unchanged.

## Constitution Check

- **Single source of truth** — spec.md drives implementation, no parallel design doc.
- **Living spec** — implementation.md will be written at completion.
- **Anchored code** — every FR/AC mapped via `# @spec` anchor comments.
- **Test coverage mandatory** — all new code path has direct tests.

## Implementation Plan (file-by-file)

### Step 1 — Enrich the canonical template
- **File:** `system/templates/command-expectations.template.md`
- **Action:** Add Section 13 with the 6 sub-sections (h3 headings). Enrich sections 1-11 prose with structured sub-fields (Inputs, Outputs, Side-effects pointers, Examples). Keep Section 12 YAML unchanged.
- **FR:** FR-001, FR-002

### Step 2 — Extend the parser to require Section 13
- **File:** `validator/expectations.py`
- **Actions:**
  - Add `"13. Demo Session"` to `REQUIRED_SECTIONS`.
  - Add `SECTION13_SUBSECTIONS` constant: 6 canonical names.
  - Add a `DemoSession` dataclass and a `_extract_demo_session()` helper that:
    - Splits Section 13 body on h3 headings (regex tolerates `### 13.1 Foo` and `### Foo`).
    - Maps detected sub-headings (fuzzy normalized) to the 6 expected slots.
    - Raises `ExpectationsInvalid` with the exact substring required by AC-009 when a slot is missing or empty.
  - Extend `ExpectationsFile` dataclass with `demo_session: DemoSession | None` (None only when migration of legacy files is permitted, but for our 20 builtins it MUST be set).
- **FR:** FR-003

### Step 3 — Migrate the 20 builtin expectations files
- **Files:** `commands/*.expectations.md` (×20)
- **Action:** For each file, rewrite to include richer sections 1-11 plus the mandatory Section 13. Each file: ≥ 3 content lines per sub-section. Use placeholders `<feature>`, `<screen>`, `<stack>`, `<path>` where appropriate. Bump `last_reviewed: 2026-05-12` for all 20.
- **FR:** FR-004, FR-013, FR-014

### Step 4 — Implement preview renderer
- **New file:** `validator/preview.py`
  - `@dataclass ProjectContext` with `stack_name`, `feature_slugs`, `screen_names`, `convention_subdomains`, each carrying a "missing/configured" boolean.
  - `def build_project_context(project_root: Path) -> ProjectContext` — reads the 4 sources; resilient to missing files.
  - `def resolve_placeholders(markdown: str, ctx: ProjectContext) -> str` — substitutes `<feature>` (latest slug or `[no features configured]`), `<screen>` (joined list or `[no screens configured]`), `<stack>` (name or `[no stack configured]`). `<path>` passthrough.
  - `def render_preview(expectations: ExpectationsFile, project_root: Path) -> PreviewReport` — assembles Markdown.
- **New file:** `validator/preview_models.py` OR inline `PreviewReport` in `preview.py`.
- **FR:** FR-006, FR-007

### Step 5 — Wire `--preview` and `--save` flags on CLI
- **File:** `validator/cli_commands/verify_output_cmd.py`
- **Actions:**
  - Add `PREVIEW_OPTION` Typer flag.
  - Add `SAVE_OPTION` flag.
  - Early branch: if `preview` set → call `_run_preview(command, project_root, save, json_out)` and return. Skip artifact resolution.
  - `_run_preview`:
    - Load expectations (project override → builtin) — reuse `load_expectations`.
    - Catch missing-Section-13 / empty-sub-section errors → emit canonical error string to stderr + exit 2.
    - Validate `.specs/` exists at `project_root` (else exit 2 with canonical message).
    - Build ProjectContext, render preview Markdown.
    - If `--save` → write `.specs/.previews/<command>-<ISO>-<random3>.md`.
    - Print Markdown (or JSON envelope when `--json`) to stdout. Exit 0.
- **FR:** FR-005, FR-008, FR-009

### Step 6 — Tests
- **New file:** `tests/test_preview.py`
  - Unit tests for `build_project_context` against tmp_path fixtures (each source present / missing / malformed).
  - Unit tests for `resolve_placeholders` covering every placeholder.
  - Unit tests for `render_preview` end-to-end on a synthetic expectations file.
- **New file:** `tests/test_verify_output_preview_cli.py`
  - Happy path (exit 0, stdout contains real feature slug).
  - `--save` writes file under `.specs/.previews/`.
  - Section 13 missing → exit 2 + canonical message.
  - Sub-section empty → exit 2 + canonical message.
  - No `.specs/` → exit 2 + canonical message.
  - `--json --preview` emits JSON envelope.
- **New file:** `tests/test_demo_session_snapshot.py`
  - Parses `commands/spec-init.expectations.md`, `test.expectations.md`, `feature.expectations.md`.
  - Asserts each has all 6 sub-sections and each sub-section has ≥ 3 non-empty content lines.
- **Update:** `tests/test_expectations.py` and `tests/test_builtin_expectations_corpus.py`
  - Ensure existing 20 files still parse after migration.
  - Adjust any test that hardcoded a 12-section count.
- **FR:** FR-011

### Step 7 — Documentation
- **File:** `commands/spec-verify-output.md` (the slash-command instructions)
  - Add `--preview` and `--save` flag docs.
  - Add the triad workflow example.
- **File:** `.specs/features/040-.../implementation.md`
  - Create after all FR are wired with the @spec anchor mapping table.
- **File:** `.specs/changelog.md` + `.specs/features/040-.../changelog.md`
  - Add entries.
- **FR:** FR-012

## Testing Strategy

- **Unit** — `validator/preview.py` functions tested in isolation with `tmp_path` fixtures simulating diverse project shapes.
- **Integration** — CLI tests via `typer.testing.CliRunner` covering all `--preview` paths.
- **Snapshot** — Three real expectations files (init, test, feature) asserted to have complete Section 13.
- **Regression** — All existing feature 039 tests run unchanged.

## Risks & Considerations

- **Risk:** Migrating 20 expectations files is high-volume tedious work; format drift between files. → Mitigation: write a single migration helper that takes (command_name, purpose_sentence, key_files_produced) and generates a Section 13 skeleton — then hand-tune each.
- **Risk:** `ExpectationsInvalid` strings need to match canonical substrings exactly for AC-008/009/010. → Mitigation: define constants in `validator/preview.py` and reuse in tests + raises.
- **Risk:** Section 13 regex may collide with legitimate `###` headings inside sub-section bodies. → Mitigation: only split at the topmost `###` level immediately following the `## 13.` heading; nested `####` are content.

## File Manifest

**New files:**
- `validator/preview.py`
- `tests/test_preview.py`
- `tests/test_verify_output_preview_cli.py`
- `tests/test_demo_session_snapshot.py`
- `.specs/features/040-expectations-rich-and-verify-preview/spec.md` (this feature)
- `.specs/features/040-expectations-rich-and-verify-preview/plan.md` (this file)
- `.specs/features/040-expectations-rich-and-verify-preview/progress.md`
- `.specs/features/040-expectations-rich-and-verify-preview/pipeline.md`
- `.specs/features/040-expectations-rich-and-verify-preview/implementation.md` (post-impl)
- `.specs/features/040-expectations-rich-and-verify-preview/changelog.md`

**Modified files:**
- `system/templates/command-expectations.template.md`
- `validator/expectations.py`
- `validator/cli_commands/verify_output_cmd.py`
- `commands/spec-verify-output.md`
- `commands/*.expectations.md` (×20)
- `tests/test_expectations.py` (minor)
- `tests/test_builtin_expectations_corpus.py` (minor)
- `.specs/changelog.md`

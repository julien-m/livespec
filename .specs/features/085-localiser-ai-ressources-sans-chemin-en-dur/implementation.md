---
created: 2026-10-13
feature: 085-localiser-ai-ressources-sans-chemin-en-dur
title: 'Implementation Map: Locate ai-ressources Without Hard-Coded Paths'
type: implementation
updated: 2026-10-13
---

# Implementation — Locate ai-ressources Without Hard-Coded Paths

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature (validator library + CLI exit paths + documentation); no visual baselines, Penflow contract `ABSENT`.

## FR Mapping — Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Shared resolution function](spec.md#fr-001) | `validator/ai_resources.py` | `@spec FR-001: Shared resolution order and source, FR-002: Dedicated error — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-001` | ✅ Implemented | 2026-10-13 |
| [FR-002: Dedicated Resolution error](spec.md#fr-002) | `validator/exceptions.py`, `validator/ai_resources.py` | `@spec FR-002: Dedicated error and message — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-002` | ✅ Implemented | 2026-10-13 |
| [FR-003: No forbidden fallback](spec.md#fr-003) | `validator/init_from_code.py`, `validator/conventions_ast/catalog.py`, `validator/conventions_ast/corpus.py`, `tests/test_ai_resources_guard.py` | `@spec FR-003: No init fallback, FR-005: Init ERROR exit 2 before any write — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-003` | ✅ Implemented | 2026-10-13 |
| [FR-004: Consumers routed through the shared resolution](spec.md#fr-004) | `validator/conventions_ast/catalog.py`, `validator/conventions_ast/corpus.py`, `validator/conventions_ast/source_decisions.py`, `validator/conventions_rules.py`, `validator/coherence/rules/r7_conventions_gates.py`, `validator/init_recovery.py` | `@spec FR-004: Route catalog through shared resolution` · `Route corpus through shared resolution` · `Decisions reuse the corpus root` · `Route compiler through shared resolution` · `Route R7.3 through shared resolution` · `Validity uses the shared root — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-004` | ✅ Implemented | 2026-10-13 |
| [FR-005: Existing reactions carry the message](spec.md#fr-005) | `validator/conventions_ast/catalog.py`, `validator/conventions_ast/corpus.py`, `validator/conventions_ast/source_decisions.py`, `validator/conventions_ast/source_decision_types.py`, `validator/conventions_rules.py`, `validator/coherence/rules/r7_conventions_gates.py`, `validator/init_recovery.py`, `validator/init_from_code.py` | `@spec FR-005: Catalog error` · `Empty manifest with error` · `Zero decisions with error` · `Decision manifest carries resolution_error` · `rulebook_error` · `One explicit ERROR` · `Unresolved root is invalid` · `Init ERROR exit 2 before any write — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-005` | ✅ Implemented | 2026-10-13 |
| [FR-006: Guard, unit and consumer tests on fake corpora](spec.md#fr-006) | `tests/conftest.py`, `tests/ai_resources_fixture.py`, `tests/test_ai_resources.py`, `tests/test_ai_resources_consumers.py`, `tests/test_ai_resources_failures.py`, `tests/test_ai_resources_guard.py` | `@spec FR-006: Fake-corpus tests ignore the caller's AIRESOURCES` · `Fake corpora for resolution and consumer tests` · `Guard test — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-006` | ✅ Implemented | 2026-10-13 |
| [FR-007: README and documents](spec.md#fr-007) | `README.md`, `.specs/spec-system.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-specify/expectations.md`, `system/templates/spec-template.md`, `tests/test_ai_resources_docs.py` | `@spec FR-007: README documents AIRESOURCES — .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-007` | ✅ Implemented | 2026-10-13 |

## AC Mapping — Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| [AC-001](spec.md#ac-001) | `tests/test_ai_resources.py` (`test_env_wins_over_recorded_existing_paths`, `test_env_is_used_without_existence_check_or_reading_conventions`, `test_relative_and_tilde_env_values_become_absolute`, `test_explicit_environ_mapping_is_honoured`) | ✅ Pass 2026-10-13 |
| [AC-002](spec.md#ac-002) | `tests/test_ai_resources.py` (`test_blank_env_falls_back_to_manifest_path[3]`, `test_index_declaration_used_when_manifest_path_missing`, `test_manifest_wins_when_manifest_and_index_disagree`, `test_relative_and_tilde_recorded_paths`, `test_unusable_manifest_falls_back_to_index[5]`) | ✅ Pass 2026-10-13 |
| [AC-003](spec.md#ac-003) | `tests/test_ai_resources.py` (`test_fix_sentence_is_exact`, `test_nonexistent_recorded_paths_raise_explicit_error`, `test_every_rejected_path_is_listed_in_order`, `test_nothing_recorded_raises_explicit_error`, `test_without_project_root_only_environment_applies`) | ✅ Pass 2026-10-13 |
| [AC-004](spec.md#ac-004) | `tests/test_ai_resources.py` (`test_no_home_or_livespec_sibling_fallback`: corpora at the temporary `~/projects/ai-ressources` and next to a patched `LIVESPEC_ROOT`; resolution, corpus manifest, AST catalog and `_prepare_documents` all report the Resolution error) | ✅ Pass 2026-10-13 |
| [AC-005](spec.md#ac-005) | `tests/test_ai_resources_consumers.py` (`test_consumer_uses_the_shared_root`: 7 consumers × 3 situations = 21 cells; the init cell observes `_prepare_documents` on the same project after making its routed source missing) | ✅ Pass 2026-10-13 |
| [AC-006](spec.md#ac-006) | `tests/test_ai_resources_failures.py` (compile text and `--json` exit 2 `rulebook_error`, `AstCatalogError`, empty corpus manifest with `ai_resources_root == ""` and `resolution_error`, zero decisions with `resolution_error`, R7.3 silent without rulebook and one ERROR with it, validity false, `init --from-code` `--dry-run` / `--force` / plain → `ERROR:`, exit 2, tree unchanged) | ✅ Pass 2026-10-13 |
| [AC-007](spec.md#ac-007) | `tests/test_ai_resources_consumers.py` (`test_other_machine_recorded_path_is_valid_with_local_env_clone`, validity cells of the matrix) | ✅ Pass 2026-10-13 |
| [AC-008](spec.md#ac-008) | `tests/test_ai_resources_consumers.py` (`test_compile_needs_no_index_declaration_with_env`, `test_compile_still_rejects_escaping_source`, `test_r7_3_still_rejects_escaping_display_path`, compile and R7.3 cells of the matrix) | ✅ Pass 2026-10-13 |
| [AC-009](spec.md#ac-009) | `tests/test_ai_resources_guard.py` | ✅ Pass 2026-10-13 |
| [AC-010](spec.md#ac-010) | `tests/test_ai_resources_docs.py` | ✅ Pass 2026-10-13 |
| [AC-011](spec.md#ac-011) | `tests/test_ai_resources*.py` (fake corpora only, `AIRESOURCES` via `monkeypatch`) and the full unit suite run with the pinned corpus and with the CI-like 7-file sparse corpus; real-corpus AST tests unchanged | ✅ Pass 2026-10-13 |

- **Latest test report:** [`checks/2026-10-13-test.md`](checks/2026-10-13-test.md) (`/spec-test --auto --update`): 11/11 AC covered and certified by a runner-owned execution receipt (75 reviewed bindings), 0 tests generated; integration 3a and full suite green with only the 8 pre-existing `origin/main` failures deselected; feature-scope conventions gate PASS; no impacted user journey.

## Success Criteria Evidence

| SC | Evidence | Status |
|---|---|---|
| [SC-001](spec.md#success-criteria) | Request grep over `validator .agent-sync system .specs/spec-system.md README.md` returns no line; `tests/test_ai_resources_guard.py` and `tests/test_ai_resources_docs.py::test_request_grep_scope_has_no_forbidden_location` | ✅ 2026-10-13 |
| [SC-002](spec.md#success-criteria) | `tests/test_ai_resources.py` runs every resolution case under the autouse `empty_home` fixture (`HOME` and `Path.home` set to an empty temporary directory, `AIRESOURCES` removed, then set per case with `monkeypatch`) | ✅ 2026-10-13 |
| [SC-003](spec.md#success-criteria) | `tests/test_ai_resources_consumers.py::test_consumer_uses_the_shared_root` (21 parametrized cells) | ✅ 2026-10-13 |
| [SC-004](spec.md#success-criteria) | Full unit suite transcript (pinned and sparse corpus) and `livespec conventions verify --feature 085-localiser-ai-ressources-sans-chemin-en-dur` PASS receipt | ✅ 2026-10-13 |

## Plan Review Findings Addressed

- `corpus._empty_manifest(root_text, *, resolution_error=None)` takes the root text, so the failure manifest's `ai_resources_root` is really `""`; `source_decisions._corpus_decisions` builds no decision when `resolution_error` is present instead of turning `""` into `Path(".")`.
- SC-002: the autouse `empty_home` fixture of `tests/test_ai_resources.py` applies to every resolution test, not only the D-06 test.
- AC-005 init cell: observed through `_prepare_documents` on the same project after its routed source is made missing, so init renders even in the recorded-path-only situation (stated in the `_init` docstring).

## Files Created/Modified

- New: `validator/ai_resources.py`; tests `tests/ai_resources_fixture.py`, `tests/test_ai_resources.py`, `tests/test_ai_resources_consumers.py`, `tests/test_ai_resources_failures.py`, `tests/test_ai_resources_guard.py`, `tests/test_ai_resources_docs.py`, `tests/test_ai_resources_isolation.py` (AC-011: the resolution, consumer and failure modules pass in a child pytest with `AIRESOURCES` unset and an empty `HOME`; real-corpus AST modules import no fake-corpus helper).
- Modified validator: `validator/exceptions.py` (error + fix sentence; one legacy one-line anchor split to drop its `noqa`), `validator/conventions_ast/{catalog,corpus,source_decisions,source_decision_types}.py`, `validator/conventions_rules.py` (declaration regex moved to `ai_resources.py`; legacy `noqa` / `type: ignore` removed), `validator/coherence/rules/r7_conventions_gates.py`, `validator/init_recovery.py`, `validator/init_from_code.py`.
- Adjusted existing tests (no assertion weakened): `tests/conftest.py` (`without_airesources` fixture) applied in tests of conventions taxonomy, source decisions and its serialization helper, SQL, CSS/Tailwind, source family checks, ARS rules, generated catalog, compile and R7.3; test-side sibling fallback removed from `tests/test_init_recovery.py`; `tests/test_init_hook_pipeline.py` sets the fixture `AIRESOURCES` before its in-process validity check.
- Documentation: `README.md`, `.specs/spec-system.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-specify/expectations.md`, `system/templates/spec-template.md`.

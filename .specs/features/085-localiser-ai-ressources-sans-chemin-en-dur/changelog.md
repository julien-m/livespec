# Changelog - 085-localiser-ai-ressources-sans-chemin-en-dur

## 2026-10-13 — [Spec]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created: four stories, eleven AC, seven FR, four SC)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-011 (all defined)
- **Author:** Claude Code native spec-specify (claude-opus-5-5)
- Read the [spec](spec.md): one shared resolution of the ai-ressources root (non-empty `AIRESOURCES`, then the existing directory recorded in `.conventions/manifest.yaml` `ai_resources_path`, then the `.conventions/index.md` declaration, else a dedicated error asking to run `./setup.sh` or export `AIRESOURCES`), routed through the six validator sites with their existing graceful reactions, a guard test against hard-coded fallbacks, and README/spec-system/spec-specify/spec-template documentation updates.
- Spec review: prepared (2 batches, model claude-opus-5-5); independent reviewer dispatch pending at the supervisor.

<!-- finalize:spec-specify:2026-10-13:e8bcdd29 -->

### 2026-10-13 — Plan: Technical plan generated

- **Type:** Feature
- **Spec modified:** No (lifecycle status only, through finalize)
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** Claude Code native spec-plan (claude-opus-5-5)
- Read the [plan](plan.md): new `validator/ai_resources.py` (`resolve_ai_resources_root`) and `AiResourcesResolutionError` in `validator/exceptions.py`; six steps routing the AST catalog, corpus and rule decision manifests, the conventions compiler, R7.3, `conventions_are_valid` and `init --from-code`; one sequence diagram; decisions D-01 to D-09 (visible `resolution_error`, rejected paths shown as absolute path plus source file, exit 2 kept, `HOME`/`LIVESPEC_ROOT` isolation, init boundary conversion, code-span documentation form); list of existing tests to adjust with a `without_airesources` fixture.
- Plan review: prepared (model claude-opus-5-5); independent reviewer dispatch pending at the supervisor.

<!-- finalize:spec-plan:2026-10-13:5f189e4f -->

### 2026-10-13 — ### Implementation: shared ai-ressources resolution routed through every consumer

- **Type:** Feature
- **Spec modified:** No (lifecycle status only: In Progress)
- **Code modified:** validator/ai_resources.py (new), validator/exceptions.py, validator/conventions_ast/{catalog,corpus,source_decisions,source_decision_types}.py, validator/conventions_rules.py, validator/coherence/rules/r7_conventions_gates.py, validator/init_recovery.py, validator/init_from_code.py, README.md, .specs/spec-system.md, .agent-sync/skills/spec-specify/SKILL.md + expectations.md, system/templates/spec-template.md, tests/conftest.py, tests/ai_resources_fixture.py, tests/test_ai_resources{,_consumers,_failures,_guard,_docs}.py, fake-corpus fixture adjustments in existing conventions/init tests
- **AC impacted:** AC-001 through AC-011 (tests passing; execution certification pending the independent mapping review)
- **Author:** Claude Code native spec-implement (claude-opus-5-5)
- Read [implementation](implementation.md) and [progress](progress.md): `resolve_ai_resources_root` (non-empty `AIRESOURCES`, then existing `ai_resources_path`, then the `index.md` declaration, else `AiResourcesResolutionError` with the `./setup.sh` fix); no `~/projects` or checkout-sibling fallback remains; consumers keep exit 2 / empty manifests (`resolution_error`) / `AstCatalogError` / one R7.3 ERROR / validity false.
- Evidence: 67 feature tests pass; full unit suite with the pinned corpus and with the CI 7-file sparse corpus: 3882 passed, 6 failed (the 6 root-only baseline failures), 28 skipped; ruff, pyright, mypy clean; request grep empty; `livespec conventions verify --feature 085-localiser-ai-ressources-sans-chemin-en-dur` PASS.
- Status stays In Progress: the acceptance mapping review is prepared (`run/acceptance/`) and its independent reviewer dispatch is left to the supervisor before execution certification.

<!-- finalize:spec-implement:2026-10-13:cedd6521 -->

### 2026-10-13 — Test: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None (no test generated; all 11 AC already covered)
- **Coverage:** 11/11 AC covered (100%), 0 generated, 69/69 feature tests passing; integration 166 passed / 27 skipped; full suite 3974 passed / 62 skipped / 0 failed (8 pre-existing origin/main failures deselected)
- **Report:** `checks/2026-10-13-test.md`
- **Author:** Claude Code native spec-test (claude-opus-5-5)
- Conventions gate PASS at feature scope; no impacted user journey; non-UI (no visual phase).

<!-- finalize:spec-test:2026-10-13:477becbc -->

### 2026-10-13 — ## [Feature]: ai-ressources located without hard-coded path

- **Type:** Feature
- **Spec modified:** Yes (status Implemented)
- **Code modified:** Yes (`validator/ai_resources.py`, six consumers, docs, tests)
- **AC impacted:** AC-001 through AC-011 (all certified by execution receipt)
- **Author:** Claude Code native spec-feature (claude-opus-5-5)
- One shared resolution (`AIRESOURCES`, then the recorded `.conventions/` path when it is an existing directory, else an explicit error asking to run `./setup.sh` or export `AIRESOURCES`) is used by init, the AST catalog, the corpus and rule decision manifests, the conventions rulebook, R7.3 and init recovery; no `~/projects` or sibling fallback remains.
- Independent native quality review: no blocking finding; README, `system/conventions-enforcement.md` and R7.3 empty-rulebook follow-ups applied.

<!-- finalize:spec-feature:2026-10-13:72cf8076 -->

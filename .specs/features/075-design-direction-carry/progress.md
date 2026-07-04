# Progress: Design Direction Carry (075)

| Step | Status | Checkpoint |
|---|---|---|
| Context | Done | Read worker brief, APEX plan, triage, APEX artifacts, and LiveSpec system rules. |
| Pre-edit gates | Done | Replayed G1-G6; seams were clean and 074 collision was detected. |
| Feature number | Done | Retargeted feature to 075 because `074-agent-device-proof-adapter` already exists. |
| Spec artifacts | Done | Created feature spec, plan, progress, implementation map, and changelog. |
| Payload edits | Done | Updated template, `spec-specify`, `spec-init`, expectations, spec-system, README, roadmap, and global changelog. |
| Tests | Done | Added static contract tests for carry-only behavior and Screens parser tolerance. |
| Targeted pytest | Done | `python3 -m pytest tests/test_design_direction_carry.py -q` passed: 6 passed. |
| Full pytest | Done | `python3 -m pytest -q` passed: 2394 passed, 40 skipped, 194 warnings. |
| Ruff check | Done | `ruff check .` passed. |
| Ruff format | Partial | `ruff format --check .` failed on six files outside this feature diff: `tests/test_conventions_diffguard.py`, `tests/test_conventions_lang_multilang.py`, `tests/test_conventions_taxonomy.py`, `tests/test_conventions_verify_scope.py`, `tests/test_journey_v2_runner.py`, `validator/conventions_gates.py`; `tests/test_design_direction_carry.py` is formatted. |
| Pyright | Done | `pyright` passed: 0 errors, 0 warnings, 0 informations. |
| LiveSpec validation | Done | `livespec validate .specs/features/075-design-direction-carry --format compact` passed after progress/changelog shape fixes. |
| Conventions verify | Partial | Feature-scoped `livespec conventions verify --feature 075-design-direction-carry --json` returned PASS; latest receipt `.specs/conventions/runs/20260704T171750Z/receipt.json`. Repo-scope `livespec conventions verify` returned FAIL with 3069 existing violations. |
| Degradation transcript V11 | Done | `checks/2026-07-04-design-direction-transcripts.md` records no-source output: 0 `Design direction` lines and 0 placeholders. |
| Default transcript V12 | Done | `checks/2026-07-04-design-direction-transcripts.md` records default-direction-only output: one exact `**Design direction:**` line. |
| Git status | Done | Final status captured on branch `orch/W-livespec-31b0`; no `migrations/**` or `VERSION` changes. |

# Progress — 060-journey-fixture-bootstrap-contract

**Command:** /spec-implement
**Goal hash:** 8035ced40b9c9633378909ce72e8b20320e34b85bc6ad9cc1ec511ccb3696616
**Started:** 2026-06-11

> Checkpoint table used by `--resume`. A step is `Done` only after its targeted tests + lint pass.

| Step | Status | Files | Tests run | Result | Updated at |
|---|---|---|---|---|---|
| 1 — Contract models, loader, path helper | Done | `validator/journeys/fixtures.py`, `validator/journeys/paths.py`, `tests/test_journey_v2_fixtures_contract.py` | `pytest tests/test_journey_v2_fixtures_contract.py -q` + ruff + pyright | Pass (9/9) | 2026-06-11 13:45 |
| 2 — resolve_bootstrap derivation | Done | `validator/journeys/fixtures.py`, `tests/test_journey_v2_fixtures_contract.py` | `pytest tests/test_journey_v2_fixtures_contract.py tests/test_journey_v2_schema.py -q` + ruff + pyright | Pass (25/25) | 2026-06-11 13:52 |
| 3 — Journey schema BootstrapOverride | Done | `validator/journeys/schema.py` (S2+S3 small combined diff: override semantics in resolve_bootstrap require the schema field; both steps' tests written RED first, then green together) | same as Step 2 | Pass | 2026-06-11 13:52 |
| 4 — Blocking contract validation | Done | `validator/journeys/validator.py`, `validator/journeys/fixtures.py` (skeleton), `tests/test_journey_v2_fixtures_contract.py` | `pytest tests/test_journey_v2_fixtures_contract.py tests/test_journey_v2_validation.py tests/test_journey_v2_schema.py -q` + ruff + pyright | Pass (39/39) | 2026-06-11 14:02 |
| 5+6 — XCUITest waits + manifest bump (atomic) | Done | `validator/journeys/compiler.py`, `validator/journeys/manifest.py`, `tests/test_journey_v2_compiler.py`, `tests/test_journeys.py` (legacy fixture updated for 057 capability gate — pre-existing failure at HEAD fixed) | `pytest tests/test_journey_v2_*.py tests/test_journeys.py -q` + ruff + pyright | Pass (123/123) | 2026-06-11 14:15 |
| 7 — Runner staleness + reclassification | Done | `validator/journeys/runner.py`, `tests/test_journey_v2_runner.py` | `pytest tests/test_journey_v2_runner.py tests/test_journey_v2_compiler.py tests/test_journey_v2_fixtures_contract.py -q` + ruff + pyright | Pass (89/89) | 2026-06-11 14:22 |
| 8 — Scaffold + CLI subcommand | Done | `validator/journeys/fixtures.py`, `validator/cli_commands/journey_cmd.py`, `tests/test_journey_v2_fixtures_contract.py` | `pytest tests/test_journey_v2_fixtures_contract.py -q` + ruff + pyright | Pass (36/36) | 2026-06-11 14:30 |
| 9 — Migration v21 | Done | `migrations/21/migrate.md`, `scripts/migrate-journeys-fixtures-scaffold.sh` (chmod +x), `VERSION` (20→21), `tests/test_journey_v2_fixtures_contract.py` (+chaos marks) | `pytest tests/test_journey_v2_fixtures_contract.py tests/test_migration_planner.py -q` + ruff | Pass (49/49) | 2026-06-11 14:38 |
| 10 — Documentation | Done | `system/testing/user-journeys.md` (Fixture Bootstrap Contract section: schema, derivation, app-side duties, staleness, 5 error codes + scaffold recovery) | `pytest tests/test_journey_v2_docs_skills.py -q` (2/2) + manual section review | Pass | 2026-06-11 14:44 |
| 11 — Full suite + quality gates | Done | — (verification step) | `pytest tests/test_journey_v2_*.py -q` (133 passed, 0 skips, SC-001); `pytest tests/ --ignore=tests/integration -q` (1882 passed, 4 pre-existing hardware-gated skips in test_ui_runner_* — identical at HEAD, outside 060 scope); `pytest tests/ -m chaos -q` (8 passed); `ruff check` + `ruff format --check` clean; `pyright validator/` 0 errors | Pass | 2026-06-11 14:50 |

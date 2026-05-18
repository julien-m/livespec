---
feature: 048-command-validation-hardening
status: Implemented
updated: 2026-05-18
---

# Progress - Command Validation Hardening

| Step | Status | Evidence |
|---|---|---|
| Command registry | Done | `validator/command_registry.py`; `tests/test_command_registry.py` |
| Command audit CLI | Done | `validator/command_audit.py`; `livespec command-audit --repo . --naming-policy hyphenated` exits 0 |
| Run finalization | Done | `validator/cli_commands/run_cmd.py`; `tests/test_command_finalization_contract.py` |
| Utility backends | Done | `validator/cli_commands/utility_cmd.py`; `tests/test_status_play_conventions_cli.py` |
| Coherence replacement | Done | `scripts/check-coherence.sh` delegates to command-audit and exits 0 |
| Migration 14 | Done | `migrations/14/migrate.md`; `tests/integration/test_migration_v14_v15.py` |
| Full tests | Done | `python3 -m pytest -q` -> 1506 passed, 32 skipped |

## Notes

`ruff` could not be run in this environment because the module is not installed.

---
feature: 049-command-naming-normalization
status: Implemented
updated: 2026-05-18
---

# Progress - Command Naming Normalization

| Step | Status | Evidence |
|---|---|---|
| Alias registry | Done | `validator/command_registry.py`; aliases tested for every command |
| Alias-aware validators | Done | `verify-output`, `run finalize`, hooks, and integrations normalize aliases |
| Hyphenated links | Done | `scripts/link-local.sh` creates `spec-*.md` and preserves `spec.*.md` |
| Bootstrap links | Done | `scripts/install.sh --dry-run` reports hyphenated and dotted bootstrap links |
| Documentation rename | Done | command docs and rules prefer `/spec-*`; dotted names remain compatibility aliases |
| Migration 15 | Done | `migrations/15/migrate.md`; `tests/integration/test_migration_v14_v15.py` |
| Canonical source filenames | Done | `commands/spec-*.md`, `commands/spec-*.expectations.md`; command-audit enforces the rule |
| Full tests | Done | `python3 -m pytest -q` -> 1509 passed, 32 skipped |

## Notes

Internal command artifact names now use the canonical `spec-<name>` command
identity. Historical `.specs/.runs/<short-name>-*.json` files remain readable
through legacy lookup fallback.

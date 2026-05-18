## 2026-05-06 - [Spec Update]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created - all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-014 (all defined)
- **Author:** spec.specify

## 2026-05-07 - [Implementation]: Preflight auto-install & init engine

- **Type:** Implementation
- **Spec modified:** No
- **Code modified:**
  - `validator/preflight_autofix.py` (new) - install/init dispatchers, smart scoping, fix loop, summary
  - `scripts/preflight-enrich.py` (new) - migration helper (driver/runner detection + manifest patch)
  - `migrations/10/migrate.md` (new) - migration v10
  - `tests/test_preflight_autofix.py` (new) - unit tests
  - `commands/spec-preflight.md` (updated) - `--fix`, `--full`, `--auto`, `--dry-run` documentation
- **AC covered:** AC-001..AC-014 (engine + migration + flags + summary)
- **Author:** spec.feature

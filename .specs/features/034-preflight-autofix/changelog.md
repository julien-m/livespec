## 2026-10-12 — [Refactor]: YAML-style manifest parsing test asserts parsed fields

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_preflight_autofix.py — `test_parse_preflight_manifest_yaml_style` only asserted `isinstance(items, list)`; it now checks the parsed name, binary, installer and verify command.
- **AC impacted:** None
- **Open defect (not fixed here):** `auto_resolve: pip install -e ".[dev]"` is classified as `pip` with `install_arg='".[dev]"'`, so `build_install_cmd` yields `pip install --user '".[dev]"'`: the `-e` flag is dropped and the shell quotes stay literal. The test does not pin that argument.
- **Author:** claude-code

---

## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

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

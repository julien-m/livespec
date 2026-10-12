# Changelog - Command Validation Hardening

## 2026-10-12 — [Refactor]: Hook template-variable sync derived from the resolvers

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_hook_resolver.py, tests/test_integrations.py
- **AC impacted:** None
- **Author:** claude-code (test-suite cleanup lot 3)

The `{{var}}` documentation check compared `system/hooks.md` with a list hard-coded in the test; known variables now come from `_build_feature_ctx` and the `commit-context write` payload. A stale `pytest.skip` on the shipped `mockups.md.example` was removed.

## 2026-09-06 — [Spec Update]: Precise traceback guard

- **AC impacted:** AC-002. Accept the exact Python traceback header with an actual newline alongside the legacy broad signature; reject missing guards. Read [feature 078](../078-requirement-evidence-integrity/spec.md) for structured review output provenance.

## 2026-05-18 — [Spec Update]: Created

- **Type:** Spec Update
- **Spec modified:** Yes (initial feature spec and plan)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-013
- **Author:** tool-name

## 2026-05-18 — [Feature]: Implemented

- **Type:** Feature
- **Spec modified:** Yes (status Draft → Implemented)
- **Code modified:** `validator/command_registry.py`, `validator/command_audit.py`, `validator/cli_commands/command_audit_cmd.py`, `validator/cli_commands/run_cmd.py`, `validator/cli_commands/utility_cmd.py`, `scripts/check-coherence.sh`, `scripts/play-coverage.sh`, `migrations/14/migrate.md`
- **AC impacted:** AC-001 through AC-013
- **Author:** codex

## 2026-10-12 — [Refactor]: Command audit tests independent of the working directory

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_command_audit_cli.py
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Paths and `--repo` are anchored on the repository root.

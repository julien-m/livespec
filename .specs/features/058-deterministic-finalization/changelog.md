# Changelog - Deterministic Finalization

## 2026-06-10 — [Spec]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-012 (all defined)
- **Author:** claude-code (/spec-specify)

## 2026-06-10 — [Plan]: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** claude-code (/spec-plan)

## 2026-06-10 — [Feature]: Deterministic Finalization implemented

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** validator/finalize.py, validator/finalize_receipt.py, validator/finalize_registry.py, validator/finalize_readme.py, validator/locks.py, validator/goal_contracts.py, validator/cli_exit_codes.py, validator/cli_commands/finalize_cmd.py, validator/cli_commands/__init__.py, tests/test_finalize.py, tests/test_locks.py, tests/test_goal_contracts.py, docs/cli-reference.md, README.md, 6× .agent-sync/skills/<cmd>/{SKILL.md,expectations.md}
- **AC impacted:** AC-001 through AC-012 (all satisfied)
- **Author:** claude-code (/spec-implement)

## 2026-06-10 — [Spec]: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None (0 tests generated — 12/12 AC already covered by TDD)
- **Coverage:** 12/12 AC covered (100%), 0 generated, 135/135 feature tests passing (incl. chaos), integration 3a 75/75
- **Report:** `checks/2026-06-10-test.md`
- **Author:** claude-code (/spec-test)

<!-- finalize:spec-implement:2026-06-10:9a1dbf71 -->

## 2026-06-10 — [Feature]: /spec-feature pipeline complete — deterministic finalization shipped

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** none (pipeline-completion entry; implementation finalized under spec-implement)
- **AC impacted:** AC-001 → AC-012 (all verified, 12/12 coverage)
- **Author:** spec-feature

<!-- finalize:spec-feature:2026-06-10:96deb6de -->

## 2026-09-06 — Lifecycle-only finalization compatibility (078)

- Read the amended [AC-002/FR-002 contract](spec.md#ac-002): spec finalization changes recognized lifecycle metadata only, never appends body markers, and preserves historical comments. Generated registries and receipts retain exact payload/status identities.
- Read the [lifecycle regressions](../../../tests/test_finalize_lifecycle.py): first/new commands, metadata transitions and new entries preserve normative bytes; genuine normative edits invalidate proof; body examples cannot replace missing actual anchors; CRLF and stale receipts remain exact.
- Validation: 243 locks/finalizer/lifecycle/Penflow/review/evidence tests pass in 15.75 seconds, including read-only real 001/077 copies and first-finalization CLI proof/archive. Scoped Ruff/format, Pyright and mypy pass. The shared writer now verifies raw persisted bytes, rejecting unexpected newline conversion. No feature078 status promotion or preparatory marker step performed.
- Read the [shared metadata parser](../../../validator/lifecycle_metadata.py): explicit Header and bounded legacy H1 introduction share the same strict limits with Normative Identity v2. No migration of the 73 existing specs without Header is required.

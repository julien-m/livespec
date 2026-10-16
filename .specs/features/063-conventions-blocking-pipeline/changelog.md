# Changelog — Conventions Blocking Pipeline

## 2026-10-12 — [Refactor]: Test suite cleanup (lot 2)

AC-006 is now proven by parsing each real `expectations.md` with `validator.expectations`. Removed a ruff-template test that re-implemented the renderer (the real scaffold is covered by `tests/test_status_play_conventions_cli.py`), a synthetic parser test superseded by the real-file check, and `test_spec_check_conventions_gate_can_use_feature_scoped_pass_receipt`, which never ran spec-check and duplicated the feature-scope PASS tests.

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** `tests/test_conventions_pipeline_docs.py`, `tests/_conventions_verify_scope_01.py`, `tests/test_conventions_verify_scope.py`
- **AC impacted:** AC-006, AC-007 (coverage kept)
- **Author:** Claude Code

## 2026-06-29 — [Bugfix]: Scope feature supervisor receipt gates to child goals

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** Updated [`validator/goal_contracts.py`](../../../validator/goal_contracts.py), [`tests/test_goal_contracts.py`](../../../tests/test_goal_contracts.py), and [`tests/test_conventions_verify_scope.py`](../../../tests/test_conventions_verify_scope.py)
- **AC impacted:** AC-004, AC-005
- **Author:** Codex

## 2026-06-25 — [Spec Update]: Fix artifact validation drift

- **Type:** Spec Update
- **Spec modified:** Yes (frontmatter added; SC-002 aligned with accepted full-test skip baseline)
- **Code modified:** None
- **AC impacted:** None
- **Author:** Codex

## 2026-06-25 — [Bugfix]: Narrow feature-scoped conventions verification

- **Type:** Bugfix
- **Spec modified:** Yes (status set to Implemented)
- **Code modified:** `validator/conventions_feature_scope.py`, `validator/conventions_gate_types.py`, `validator/conventions_gate.py`, `tests/test_conventions_verify_scope.py`, `.specs/features/.DS_Store`
- **AC impacted:** AC-007, AC-008
- **Author:** Codex

## 2026-06-25 — [Check]: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** 25/25 verified (100%), 0 partial, 0 missing; convention gate PASS; Feature 063 artifact validation PASS; project-wide tree validation PASS
- **Report:** `checks/2026-06-25.md`
- **Author:** Codex

## 2026-06-25 — [Bugfix]: Emit conventions receipts from verify CLI

- **Type:** Bugfix
- **Spec modified:** Yes (AC-007 repo-scope `--feature repo` clarification)
- **Code modified:** `validator/cli_commands/conventions_cmd.py`, `tests/test_conventions_verify.py`, `tests/test_goal_contracts.py`, `tests/test_conventions_pipeline_docs.py`, `.agent-sync/skills/spec-fix/SKILL.md`, `.agent-sync/skills/spec-implement/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-implement/expectations.md`, `system/conventions-enforcement.md`
- **AC impacted:** AC-004, AC-005, AC-007, AC-008
- **Author:** Codex

## 2026-06-13 — [Bugfix]: Wire supervisor gate CLI and tighten gates

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `validator/cli_commands/utility_cmd.py`, `validator/conventions_diffguard.py`, `validator/coherence/rules/r7_conventions_gates.py`, `validator/goal_contracts.py`, `validator/verify_output.py`
- **AC impacted:** AC-003, AC-004, AC-010, AC-011, AC-013, AC-014, AC-015
- **Author:** Codex

## 2026-06-13 — [Feature]: Blocking conventions pipeline wiring

- **Type:** Feature
- **Spec modified:** Yes (created feature spec, plan, implementation mapping, progress)
- **Code modified:** `validator/run_receipts.py`, `validator/verify_output.py`, `validator/expectations.py`, `validator/goal_contracts.py`, `validator/coherence/rules/r7_conventions_gates.py`, `validator/conventions_diffguard.py`
- **AC impacted:** AC-001 through AC-015
- **Author:** Codex

## 2026-10-16 — [Bugfix]: Resolve mapped CI configuration and documentation as feature scope while preserving source checks and scope boundaries

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** README.md, tests/test_conventions_noncode_scope.py, validator/conventions_feature_scope.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_conventions_noncode_scope.py::test_cli_verify_ci_only_scope_writes_receipt
- **RED receipt:** `.specs/.execution/b45af31ce51b4f919e0752f5546119b6/receipt.json`
- **GREEN receipt:** `.specs/.execution/1b3896287423475883ad899d443017eb/receipt.json`
<!-- bugfix:1b3896287423475883ad899d443017eb -->

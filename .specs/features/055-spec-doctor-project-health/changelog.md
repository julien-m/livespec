# Changelog — 055 Spec Doctor Project Health

## 2026-06-03 — [Bugfix]: Add downstream migration for spec-doctor

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `migrations/18/migrate.md`, `VERSION`, `tests/integration/test_migration_v18_agent_sync.py`
- **Docs modified:** `implementation.md`
- **AC impacted:** AC-014
- **Author:** Codex

## 2026-06-03 — [Check]: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** `validator/goal_contracts.py`, `tests/test_goal_contracts.py`
- **Checks modified:** `checks/2026-06-03.md`
- **Coverage:** 26/26 verified (100%), 0 partial, 0 missing
- **Report:** `checks/2026-06-03.md`
- **AC impacted:** AC-001 through AC-014 verified
- **Author:** Codex

## 2026-06-02 — [Feature]: Implement project doctor command

- **Type:** Feature
- **Spec modified:** Yes (status/branch metadata)
- **Code modified:** `validator/doctor/*`, `validator/cli_commands/doctor_cmd.py`, `validator/cli_commands/__init__.py`, `tests/test_doctor.py`
- **Docs modified:** `README.md`, `.agent-sync/skills/spec-doctor/SKILL.md`, `.agent-sync/skills/spec-doctor/expectations.md`
- **AC impacted:** AC-001 through AC-014
- **Author:** Codex

## 2026-10-12 — [Bugfix]: doctor reports suppressed in-progress coherence findings as INFO and attributes them via dir_name

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** tests/test_doctor_coherence_suppressed.py, validator/coherence/rules/r3_spec_anchors.py, validator/doctor/scanner.py
- **AC impacted:** FR-004
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_doctor_coherence_suppressed.py::test_doctor_attributes_settled_coherence_violation_to_its_feature
- **RED receipt:** `.specs/.execution/a2612583165a449781b5cba2b3e8bc9d/receipt.json`
- **GREEN receipt:** `.specs/.execution/29e0ed33a36c426d820ee14eff9a020d/receipt.json`
<!-- bugfix:29e0ed33a36c426d820ee14eff9a020d -->

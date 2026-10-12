---
title: Autonomous From-Code Recovery implementation
feature: 080-autonomous-from-code-recovery
---

# Implementation — Autonomous From-Code Recovery

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | validator/init_profile.py, init_documents.py, init_from_code.py | FR-001 | Functional tests PASS (unsupported manifests recorded, missing-manager warning); formal certification pending | 2026-10-12 |
| FR-002 | validator/init_documents.py, init_probes.py, init_verification.py | FR-002 | Functional tests PASS; formal certification pending | 2026-10-09 |
| FR-003 | validator/init_from_code.py, init_recovery.py, scripts/init-from-code-autonomous.sh, init.sh, sync-agent-assets.sh | FR-003 | Functional tests PASS; formal certification pending | 2026-10-09 |
| FR-004 | validator/goal_inventory.py, goal_contract_model.py, canonical spec-init skill | FR-004 | Functional tests PASS; formal certification pending | 2026-10-09 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | tests/test_init_profile.py, test_init_documents.py, test_init_recovery.py | Observed targeted PASS |
| AC-002 | tests/test_init_profile.py, test_init_recovery.py | Observed targeted PASS |
| AC-003 | tests/test_init_probes.py, test_init_recovery.py | Observed targeted PASS |
| AC-004 | tests/test_init_recovery.py, test_init_agent_isolation.py | Observed targeted PASS |
| AC-005 | tests/test_init_recovery.py, test_init_agent_isolation.py | Observed targeted PASS |
| AC-006 | tests/test_init_goal_profiles.py, test_goal_contracts.py | Observed targeted PASS |
| AC-007 | tests/test_init_profile.py, test_init_documents.py, test_init_recovery.py | Observed targeted PASS |

## Execution and Limits

207 focused tests passed in 48.17 seconds. Ruff and Pyright for new init modules passed. Actual backend with real cc-hub, Bun and Cargo completed fresh initialization, force recovery and readonly verification on a temporary hybrid fixture. Actual mutable-agent builds left shared hashes unchanged. No Handy write, application build/UI/runtime claim, commit or branch occurred. Backend does not execute after-init Markdown hooks; native command execution must apply them and archive authentic proofs.

Formal execution evidence/reviews and final feature/repo conformity remain uncertified. Existing immutable goals are preserved; no Implemented status is manually assigned.

## Main delivery validation

The delivery snapshot starts at origin/main b468d0a and preserves its existing fixes. Its identifier is 080 because the remote already uses 079 for Validator CI Prerequisites. Historical local goal identities remain unchanged. Shipping uses explicit AIRESOURCES configuration before the original sibling default, with a regression test for a configured path containing spaces.

Handy initialization separately completed 49/49 proofs and an authentic successful archive on 2026-10-09, preserving its 389 source files, HEAD and main branch. Handy was not executed by the delivery worker. Repository-wide feature/conventions certification remains incomplete.

Shipping also supplies the four required bootstrap convention documents through CI's existing pinned sparse checkout. The corpus revision, credential policy and cleanup are unchanged. A pre-existing archive test's membership guard uses a tuple so Mypy narrows its Literal; archive runtime bytes are unchanged and its seven regressions pass.

## 2026-10-12 — Bounded probes and hermetic init tests (spec-fix)

- `_kill_group` in [init_probes.py](../../../validator/init_probes.py) also ignores EPERM: macOS returns it while a killed group only holds zombies (reproduced 1/200).
- Budget tests drive `run_command` from a fake monotonic clock and record the real wait timeouts ([init_clock_support.py](../../../tests/init_clock_support.py)), so they assert the remaining budget instead of wall-clock bounds.
- Init tests set `AIRESOURCES` to a fixture corpus, never a sibling or private checkout.

## 2026-10-12 — Unsupported manifests and missing-manager warning (spec-fix, FR-001 decision)

- [init_profile.py](../../../validator/init_profile.py) records each recognized unsupported manifest (`UNSUPPORTED_MANIFESTS`, including the Tauri JSON5/TOML formats that previously failed) in `ObservedProfile.unsupported_manifests` without parsing it, and continues with the supported ecosystems; with no supported manifest the error names the unsupported files. A `package.json` without manager evidence adds `MISSING_MANAGER_WARNING` to `ObservedProfile.warnings` and never fails or defaults to npm.
- [init_documents.py](../../../validator/init_documents.py) renders an `Observation Findings` section in `project.md` and in the completed recap (`render_recap`) only when findings exist, so profiles without findings keep identical bytes; [init_from_code.py](../../../validator/init_from_code.py) prints `WARNING:` lines on stderr in every mode. `bootstrap-profile.json` carries both new fields through `asdict`.
- RED then GREEN: 10 new cases in [profile tests](../../../tests/test_init_profile.py), [document tests](../../../tests/test_init_documents.py) and a real subprocess run in [recovery tests](../../../tests/test_init_recovery.py) (dry-run and completed run, written profile/report, read-only verification).

---
type: implementation
feature: 004-visual-testing-governance
created: 2026-04-14
updated: 2026-04-14
---

# Implementation Map: Visual Testing Governance

## FR/AC to Source Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Write baseline.manifest.yml after approval](spec.md#fr-001) | `.claude/commands/spec.test.md` (Phase 4.5.3 Step D) | `<!-- @spec FR-001: Write baseline.manifest.yml after approval -->` | ✅ Implemented | 2026-04-14 |
| [FR-002: --show-provenance flag](spec.md#fr-002) | `.claude/commands/spec.check.md` (Step 3.1) | `<!-- @spec FR-002: show-provenance flag reads and displays manifest -->` | ✅ Implemented | 2026-04-14 |
| [FR-003: Staleness check before comparison](spec.md#fr-003) | `.agent-sync/skills/spec-check/SKILL.md`, `validator/visual_gate.py`, `validator/registry_links.py` | `@spec FR-003` in command docs and visual gate validator | ✅ Implemented | 2026-05-23 |
| [FR-004: Mockup hash detection](spec.md#fr-004) | `.agent-sync/skills/spec-check/SKILL.md`, `validator/visual_gate.py`, `validator/registry_links.py`, `tests/test_visual_implementation_gate.py` | Legacy `screens[].mockup_version` validation with optional `mockup_path` | ✅ Implemented | 2026-05-23 |
| [FR-005: Browser version detection](spec.md#fr-005) | `.claude/commands/spec.check.md` (Step 8.0 — playwright --version) | same anchor as FR-003 | ✅ Implemented | 2026-04-14 |
| [FR-006: --visual-status governance dashboard](spec.md#fr-006) | `.claude/commands/spec.check.md` (Step 8.5) | `<!-- @spec FR-006: visual-status flag scans all features and classifies baselines -->` | ✅ Implemented | 2026-04-14 |
| [FR-007: baseline.manifest.yml schema](spec.md#fr-007) | `system/schemas/baseline-manifest.md` | `<!-- @spec FR-007: baseline manifest schema definition -->` (file header) | ✅ Implemented | 2026-05-23 |
| [FR-008: migrations/5/migrate.md](spec.md#fr-008) | `migrations/5/migrate.md` | `<!-- @spec FR-008: migration v5 manifest -->` (file header) | ✅ Implemented | 2026-04-14 |

## Acceptance Criteria Mapping

| AC | Description | File/Evidence | Status |
|---|---|---|---|
| AC-001 | spec.test writes `baseline.manifest.yml` after every baseline approval | spec.test.md Phase 4.5.3 Step D + DoD checklist | ✅ Implemented |
| AC-002 | Manifest records all required fields per screen plus optional `mockup_path` | spec.test.md Step D data collection table; system/schemas/baseline-manifest.md schema | ✅ Implemented |
| AC-003 | `spec.check --show-provenance` displays manifest as table | spec.check.md Step 3.1 + Flags table | ✅ Implemented |
| AC-004 | Missing manifest triggers WARNING (not error) | spec.check.md Step 3.1 missing manifest path + Step 8.0 staleness gate | ✅ Implemented |
| AC-005 | spec.check Step 8 resolves `mockup_path` or default same-name mockup and detects missing/stale hashes | `validator/visual_gate.py`, `tests/test_visual_implementation_gate.py` | ✅ Implemented |
| AC-006 | Stale baselines are NOT used for pixel comparison | spec.check.md Step 8.0 classification table (VALID only → comparison) | ✅ Implemented |
| AC-007 | Stale baselines produce WARNING exit, not ERROR | spec.check.md Step 8.0 "EXIT code for stale baselines: WARNING" | ✅ Implemented |
| AC-008 | spec.check detects browser version changes via playwright --version | spec.check.md Step 8.0 browser version check | ✅ Implemented |
| AC-009 | Browser version change marks ALL baselines STALE-BROWSER | spec.check.md Step 8.0 "mark ALL screens for this feature as STALE-BROWSER" | ✅ Implemented |
| AC-010 | `spec.check --visual-status` scans all features and classifies baselines | spec.check.md Step 8.5 + Flags table | ✅ Implemented |
| AC-011 | `spec.check --visual-status` prints action summary | spec.check.md Step 8.5 Action Required section | ✅ Implemented |
| AC-012 | Migration v5 generates manifest stubs for existing baselines | migrations/5/migrate.md GENERATE_STUB action | ✅ Implemented |

## Files Created/Modified

| File | Action | Description |
|---|---|---|
| `system/schemas/baseline-manifest.md` | Created | Canonical YAML schema for baseline.manifest.yml — field definitions, examples, validation rules |
| `validator/visual_gate.py` | Modified | Validates legacy `screens[].mockup_version`, resolves optional `mockup_path`, blocks missing mockups, fails stale mockup hashes |
| `validator/registry_links.py` | Modified | Adds `manifest_mockup_sha_mismatch` link violation kind |
| `.claude/commands/spec.test.md` | Modified | Phase 4.5.3 Step D: manifest write after approval; DoD checklist updated |
| `.claude/commands/spec.check.md` | Modified | Step 3.1: --show-provenance; Step 8.0: Staleness Gate (mockup hash + browser version); Step 8.5: --visual-status governance dashboard; Flags table updated; Overview updated |
| `migrations/5/migrate.md` | Created | Migration v5: GENERATE_STUB for existing baselines, IDEMPOTENCY_CHECK, SET_VERSION 5 |
| `tests/test_baseline_manifest.py` | Created | 41 unit tests covering all 8 FRs and 12 ACs |
| `tests/test_visual_implementation_gate.py` | Modified | Regression tests for missing legacy mockup, stale legacy mockup hash, and runtime-state to mockup-path mapping |
| `tests/fixtures/baseline_manifest/valid_manifest.yml` | Created | Valid manifest fixture (2 screens) |
| `tests/fixtures/baseline_manifest/stub_manifest.yml` | Created | Migration v5 stub fixture (pre-v5 untracked) |
| `tests/fixtures/baseline_manifest/corrupted_manifest.yml` | Created | Corrupted YAML fixture for error-handling tests |
| `.specs/features/004-visual-testing-governance/plan.md` | Created | Technical implementation plan |
| `.specs/features/004-visual-testing-governance/progress.md` | Created | Step-by-step implementation checkpoints |

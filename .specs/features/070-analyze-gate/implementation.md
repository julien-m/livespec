---
created: 2026-06-27
feature: 070-analyze-gate
title: 'Implementation Map: Analyze Gate'
type: implementation
updated: 2026-06-27
---

# Implementation Map: Analyze Gate (070)

**Status:** Implemented (mapped to pre-existing committed code — commit `c519f40`)
**Mode:** Retroactive specification / mapping. No working code was rewritten; this pass maps each
requirement to the already-shipped implementation and adds short `@spec` traceability anchors.

> The Analyze gate was implemented and committed before this LiveSpec feature folder existed
> (dogfooding: the gate ran on this feature's own `spec.md`/`plan.md` at Phase 2.6 and reported
> 0 CRITICAL / 0 HIGH). This document records the requirement → code mapping and the tests that
> protect each behavior.

## Requirement Mapping

| Req | Behavior | Source File | @spec Anchor | Test |
|---|---|---|---|---|
| FR-001 | Analyze gate via `validate --pre-impl`; `analyze` phase after plan-review, before preflight; no new command | `validator/cli.py` (`--pre-impl` branch), `validator/pipeline.py` (`PHASE_ORDER`) | @spec(FR-001) | `tests/test_pre_impl_analysis_cli.py`, `tests/test_pipeline.py` |
| FR-002 | Read-only cross-artifact analysis, never writes | `validator/pre_impl_analysis.py` — `analyze_feature_artifacts` | @spec(FR-002) | `tests/test_pre_impl_analysis.py` |
| FR-003 | Missing spec.md/plan.md → CRITICAL artifact finding | `validator/pre_impl_analysis.py` — missing-artifact loop | @spec(FR-003) | `tests/test_pre_impl_analysis.py` |
| FR-004 | Constitution MUST NOT phrase in spec/plan → CRITICAL | `validator/pre_impl_analysis.py` — `_constitution_violations` | @spec(FR-004) | `tests/test_pre_impl_analysis.py` |
| FR-005 | Requirement covered iff token in plan/impl, else HIGH | `validator/pre_impl_analysis.py` — coverage loop | @spec(FR-005) | `tests/test_pre_impl_analysis.py` |
| FR-006 | Deterministic `AN-<cat>-<sha1[:8]>` finding id | `validator/pre_impl_analysis.py` — `_finding_id` | @spec(FR-006) | `tests/test_pre_impl_analysis.py` |
| FR-007 | Severity domain CRITICAL/HIGH/MEDIUM/LOW | `validator/pre_impl_analysis.py` — `AnalyzeSeverity` | @spec(FR-007) | `tests/test_pre_impl_analysis.py` |
| FR-008 | Blocking iff any CRITICAL/HIGH; CLI exit 1/0 | `validator/pre_impl_analysis.py` — `has_blocking_findings`; `validator/cli.py` exit | @spec(FR-008) | `tests/test_pre_impl_analysis_cli.py` |
| FR-009 | Render report markdown + json | `validator/pre_impl_analysis.py` — `render_report_markdown`/`render_report_json` | @spec(FR-009) | `tests/test_pre_impl_analysis.py` |
| FR-010 | `--pre-impl` read-only early exit, no checks/changelog/src | `validator/cli.py` — `--pre-impl` branch | @spec(FR-010) | `tests/test_pre_impl_analysis_cli.py` |
| FR-011 | `coverage_percent` closed-form, 100.0 when none | `validator/pre_impl_analysis.py` — coverage_percent | @spec(FR-011) | `tests/test_pre_impl_analysis.py` |

## AC Coverage

| AC | Covered by | Status |
|---|---|---|
| AC-001 | analyze phase position + no new command (`test_pipeline`, CLI test) | Implemented |
| AC-002 | `analyze_feature_artifacts` writes no file | Implemented |
| AC-003 | missing spec.md/plan.md → CRITICAL | Implemented |
| AC-004 | constitution MUST NOT violation → CRITICAL | Implemented |
| AC-005 | uncovered requirement → HIGH | Implemented |
| AC-006 | requirement referenced in plan/impl → covered | Implemented |
| AC-007 | deterministic finding id stable across reruns | Implemented |
| AC-008 | severity domain bounded (CRITICAL/HIGH only where defined) | Implemented |
| AC-009 | `has_blocking_findings` + CLI exit 1/0 | Implemented |
| AC-010 | findings table + coverage matrix + metrics rendered | Implemented |
| AC-011 | `--pre-impl` read-only; missing implementation.md non-fatal | Implemented |
| AC-012 | `coverage_percent = covered/total*100` (100.0 when none) | Implemented |

## Success Criteria → Verification

| SC | Verification |
|---|---|
| SC-001 | `pytest tests/test_pre_impl_analysis.py tests/test_pre_impl_analysis_cli.py` green (all P1 ACs) |
| SC-002 | `tests/test_pre_impl_analysis.py` asserts identical findings/IDs across 2 runs |
| SC-003 | `tests/test_pre_impl_analysis_cli.py` asserts exit 1 on blocking, 0 otherwise |
| SC-004 | `tests/test_pipeline.py` asserts `analyze` phase between plan-review and preflight |

## Anchors added this pass

`validator/pre_impl_analysis.py`: @spec(FR-002), (FR-003), (FR-004), (FR-005), (FR-006), (FR-007), (FR-008), (FR-009), (FR-011).
`validator/cli.py`: @spec(FR-001), (FR-008), (FR-010).
`validator/pipeline.py`: @spec(FR-001) (analyze phase).
`tests/test_pre_impl_analysis.py`, `tests/test_pre_impl_analysis_cli.py`: traceability headers.

## Verification

- `pytest tests/test_pre_impl_analysis.py tests/test_pre_impl_analysis_cli.py` — analyzer + CLI suites green.
- Full suite (`pytest`) — no regression.
- Analyze gate dogfood (`livespec validate --pre-impl .specs/features/070-analyze-gate/`) — 0 CRITICAL / 0 HIGH, 100% coverage, exit 0.
- `livespec doctor` — target 0/0/0/0.

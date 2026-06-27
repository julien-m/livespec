---
created: 2026-06-27
feature: 069-clarify-gate
title: 'Implementation Map: Clarify Gate'
type: implementation
updated: 2026-06-27
---

# Implementation Map: Clarify Gate (069)

**Status:** Implemented (mapped to pre-existing committed code — commit `c519f40`)
**Mode:** Retroactive specification / mapping. No working code was rewritten; this pass maps each
requirement to the already-shipped implementation and adds `@spec` traceability anchors.

> The Clarify gate was implemented and committed before this LiveSpec feature folder existed
> (dogfooding: the gate ran on this feature's own `spec.md` at Phase 1.6). This document records the
> requirement → code mapping and the tests that protect each behavior.

## Requirement Mapping

| Req | Behavior | Source File | @spec Anchor | Test |
|---|---|---|---|---|
| FR-001 | Integrated phase after spec-review, before plan; no new command surface | `validator/pipeline.py` — PHASE_ORDER places clarify between spec-review and plan; orchestrated inline by spec-feature SKILL Phase 1.6 (main-context gate, no new command) | @spec(FR-001) | `tests/test_pipeline.py -k clarify` |
| FR-002 | Detect vague quality adjectives without a measurable criterion | `validator/clarify_gate.py` — VAGUE_ADJECTIVES, scan loop | @spec(FR-002) | `tests/test_clarify_gate.py::test_vague_adjective_without_metric_is_flagged_but_metric_sentence_is_not`, `tests/test_clarify_gate.py::test_every_seed_adjective_is_detected` |
| FR-003 | Requirement-ID / identifier digits do not count as a numeric criterion | `validator/clarify_gate.py` — _REQUIREMENT_RE, _METRIC_RE, _has_metric | @spec(FR-003) | `tests/test_clarify_gate.py::test_digit_inside_identifier_is_not_treated_as_a_metric` |
| FR-004 | Detect NEEDS CLARIFICATION placeholders and ASSUMED/TBD assumptions | `validator/clarify_gate.py` — _CLARIFICATION_MARKER_RE, _ASSUMPTION_MARKER_RE | @spec(FR-004) | `tests/test_clarify_gate.py::test_placeholder_and_assumption_markers_are_detected` |
| FR-005 | Rank opportunities by Impact × Uncertainty | `validator/clarify_gate.py` — ClarifyOpportunity.score, rank_clarification_opportunities | @spec(FR-005) | `tests/test_clarify_gate.py::test_ranking_prefers_higher_score_and_caps_at_five` |
| FR-006 | Deterministic, reproducible ranking (closed-form, stable sort) | `validator/clarify_gate.py` — rank_clarification_opportunities sort key | @spec(FR-006) | `tests/test_clarify_gate.py::test_ranking_is_deterministic_regardless_of_scan_order` |
| FR-007 | Cap the ranked question queue at 5 | `validator/clarify_gate.py` — rank_clarification_opportunities limit=5 | @spec(FR-007) | `tests/test_clarify_gate.py::test_ranking_prefers_higher_score_and_caps_at_five` |
| FR-008 | Write accepted answers under a dated "## Clarifications" / "### Session" heading, one bullet each, no duplicate session bullet | `.agent-sync/skills/spec-feature/SKILL.md` § Phase 1.6 step 5 | @spec(FR-008) | dogfood: this feature's own Clarifications section |
| FR-009 | Update affected FR/AC text in place (not only the Clarifications log) | spec-feature SKILL § Phase 1.6 step 5 (orchestration prose) | (orchestration) | dogfood |
| FR-010 | Empty queue → record "no ambiguities" and continue to plan | spec-feature SKILL § Phase 1.6 step 3 (orchestration prose) | (orchestration) | dogfood |
| FR-011 | auto mode: accept only deterministic recommendations, else BLOCK for human answer | `.agent-sync/skills/spec-feature/SKILL.md` § Phase 1.6 step 4 | @spec(FR-011) | dogfood |
| FR-012 | Re-validate spec via livespec validate after every write; fix-and-revalidate loop | `.agent-sync/skills/spec-feature/SKILL.md` § Phase 1.6 step 6 | @spec(FR-012) | dogfood |

## AC Coverage

| AC | Covered by | Status |
|---|---|---|
| AC-001 | clarify phase runs after spec-review, before plan (test_pipeline -k clarify) | Implemented |
| AC-002 | vague adjective without metric flagged; metric sentence not flagged | Implemented |
| AC-003 | identifier/requirement-ID digit not treated as a metric | Implemented |
| AC-004 | NEEDS CLARIFICATION / ASSUMED / TBD marker categories detected | Implemented |
| AC-005 | ranking ordered by Impact × Uncertainty score | Implemented |
| AC-006 | ranking deterministic regardless of scan order | Implemented |
| AC-007 | ranked queue capped at 5 | Implemented |
| AC-008 | accepted answers written under dated Clarifications heading, no duplicate session bullet | Implemented (dogfood) |
| AC-009 | affected FR/AC text updated in place | Implemented (dogfood) |
| AC-010 | empty queue records no-ambiguities and continues | Implemented |
| AC-011 | auto mode blocks when a human answer is required | Implemented |
| AC-012 | spec re-validated after each write (fix-and-revalidate loop) | Implemented |

## Success Criteria → Verification

| SC | Verification |
|---|---|
| SC-001 | `pytest tests/test_clarify_gate.py` green (all P1 ACs) |
| SC-002 | `tests/test_clarify_gate.py::test_ranking_prefers_higher_score_and_caps_at_five` asserts len(...) <= 5 |
| SC-003 | `tests/test_clarify_gate.py::test_ranking_is_deterministic_regardless_of_scan_order` asserts identical output |
| SC-004 | `tests/test_pipeline.py -k clarify` asserts phase order and absence of a new command |

## Anchors added this pass

`validator/clarify_gate.py`: @spec(FR-002), (FR-003), (FR-004), (FR-005), (FR-006), (FR-007).
`validator/pipeline.py`: @spec(FR-001).
`tests/test_clarify_gate.py`: traceability header @spec(FR-002..FR-007).

## Verification

- `pytest tests/test_clarify_gate.py` — clarify gate unit suite green.
- Full suite (`pytest`) — no regression (2242 passed).
- Deterministic Analyze gate (`validator/pre_impl_analysis.analyze_feature_artifacts`) — 0 CRITICAL/HIGH findings after SC coverage added to `plan.md`.
- `livespec doctor` — 0/0/0/0.

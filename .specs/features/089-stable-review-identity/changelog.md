# Changelog - 089-stable-review-identity

## 2026-10-13 — [Feature]: Reviews stay current until requirements change; one spec revision during implementation

- **Type:** Feature
- **Spec modified:** Yes (refined: narrowed to staleness, two stories, six AC, six FR; the configured model and budget moved to 093)
- **Code modified:** validator/semantic/review_stability.py (new), validator/delivery/revision.py (new), review_contract.py, review_receipts.py, review_api.py, review_synthesis.py, clarify_inventory.py, semantic_analysis.py, pre_impl_analysis.py, progression_gate.py, delivery/lane.py, delivery/review.py, cli_commands/delivery_cmd.py, system/review-protocol.md, system/delivery-review.md, spec-implement skill
- **AC impacted:** AC-001 through AC-006
- A spec or plan review becomes stale only when the FR or AC sections, the FR/AC definitions or the Gherkin blocks change (or another normative source does), not for edge cases, Quality Engineering, scope or formatting; the review budget no longer counts. `livespec delivery revision open|close|status` lets the spec be revised during implementation with one new review at the end. Acceptance, mapping and delivery reviews stay strict.
- Origin: maintainer request (13 October 2026).

## 2026-10-13 — [Feature]: Specified (spec and plan, not implemented)

- **Type:** Feature
- **Spec modified:** Yes (created, status Draft)
- **Code modified:** No
- Read [spec](spec.md) and [plan](plan.md). Origin: Handy program findings.

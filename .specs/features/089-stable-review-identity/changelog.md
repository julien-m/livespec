# Changelog - 089-stable-review-identity

> The carried warnings on the unauthenticated revision record and on empty linked documents are fixed by [094](../094-verified-review-continuity/changelog.md).

## 2026-10-13 — [Feature]: Reviews stay current until requirements change; one spec revision during implementation

- **Type:** Feature
- **Spec modified:** Yes (refined: narrowed to staleness, two stories, six AC, six FR; the configured model and budget moved to 093)
- **Code modified:** validator/semantic/review_stability.py (new), validator/delivery/revision.py (new), review_contract.py, review_receipts.py, review_api.py, review_synthesis.py, clarify_inventory.py, semantic_analysis.py, pre_impl_analysis.py, progression_gate.py, delivery/lane.py, delivery/review.py, cli_commands/delivery_cmd.py, system/review-protocol.md, system/delivery-review.md, spec-implement skill
- **AC impacted:** AC-001 through AC-006
- A spec or plan review becomes stale only when the FR or AC sections, the FR/AC definitions or the Gherkin blocks change (or another normative source does), not for edge cases, Quality Engineering, scope or formatting; the review budget no longer counts. `livespec delivery revision open|close|status` lets the spec be revised during implementation with one new review at the end. Acceptance, mapping and delivery reviews stay strict.
- Origin: maintainer request (13 October 2026).
- Delivery review round 1 (review and audit BLOCKED, two native agents) fixed: the stored context must prepare again to the receipt's hash (a consistent edit of the receipt was accepted); a review prepared with a larger budget stays current when the default budget cannot hold the context; the contest applies only to a High the reviewed spec declared; a malformed revision record blocks `verify` and progressions with `spec_revision_malformed` instead of crashing; two functions back under 50 lines. Warnings fixed too: SC ids and decorated FR/AC headings count, the strictest batch QE assessment is kept, `revision open` refuses pre-089 receipts, and a terminal pipeline update is refused while a revision is open.
- Delivery review round 2 (review and audit BLOCKED on one function over 50 lines) fixed: the terminal pipeline check moved to a helper; an empty canonical source keeps the stable path; tests for the strictest multi-batch QE assessment. Carried warnings: the revision record is local state, not authenticated (completion and `delivery review verify` still require current reviews); a terminal pipeline update through a phase without a progression gate does not recheck reviews (as before 089); setext headings are not requirement sections; no multi-batch stable verification test.
- Delivery review round 3 (final): review PASS and audit PASS by two distinct native agents. Further carried warning: an empty linked document whose role is not canonical (for example an informative link) makes the stable path fail closed; storing the source roles in the receipt would fix it.

## 2026-10-13 — [Feature]: Specified (spec and plan, not implemented)

- **Type:** Feature
- **Spec modified:** Yes (created, status Draft)
- **Code modified:** No
- Read [spec](spec.md) and [plan](plan.md). Origin: Handy program findings.

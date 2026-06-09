## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog — 005-ui-behavioral-testing

## 2026-04-14 — Check: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** 9/9 FR verified (100%), 13/13 AC verified (100%), 0 missing, 0 partial
- **Report:** `checks/2026-04-14.md`
- **Author:** livespec-verifier

## 2026-04-14 — Plan: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** livespec-plan-agent

## 2026-04-14 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-013 (all defined)
- **Author:** spec.specify

---

## 2026-04-15 — Audit: Post-implementation improvements applied

- **Type:** Audit Review
- **Spec modified:** Yes (spec.md line 17 status: Draft → Planned)
- **Code modified:** system/testing/ui-behavioral-taxonomy.md (versioning v1.0.0 + detection examples for 5 traits), system/testing/taxonomy-review-process.md (created), .specs/features/005-ui-behavioral-testing/tests/ (3 .feature files created)
- **AC impacted:** None (improvements to existing artifacts, no AC changes)
- **Author:** audit-review

## Backlog — Feature 006 Candidate

### /spec.stats --behavioral (behavioral metrics dashboard)

Identified during post-implementation audit (2026-04-15). Not implemented in feature 005 — requires populated behavioral AC data to be useful.

**What it does:**
- Scans all `spec.md` files for `## Behavioral AC` sections
- Counts trait frequency across all features
- Detects false positives (Behavioral AC in non-UI features)
- Reports unclassified component candidates for taxonomy review

**Why deferred:**
- Feature 005 is the first feature with Behavioral AC — dashboard would be empty
- Requires ≥10 features with behavioral data to produce meaningful signal
- Implement as part of feature 006 or as a standalone utility once adoption grows

**Acceptance criteria (draft):**
- [ ] Scans `.specs/features/*/spec.md` for `## Behavioral AC` sections
- [ ] Displays trait frequency table
- [ ] Flags features where Behavioral AC traits don't match the taxonomy (stale versions)
- [ ] Reports coverage: % of features with behavioral traits vs. total

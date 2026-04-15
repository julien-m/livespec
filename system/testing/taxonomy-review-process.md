# UI Behavioral Taxonomy — Quarterly Review Process

<!-- @spec FR-001: Behavioral taxonomy maintenance — .specs/features/005-ui-behavioral-testing/spec.md#fr-001 -->

> Governance process for keeping the behavioral taxonomy current and accurate.
> Companion document to [`ui-behavioral-taxonomy.md`](ui-behavioral-taxonomy.md).

**Frequency:** Quarterly (every 3 months)
**Owner:** Project lead / spec maintainer
**First review due:** 2026-07-14

---

## Review Checklist

Run on a new component sample (≥10 components from recent project work):

- [ ] Crash test: classify each component against the current 5 traits
- [ ] Classification rate ≥ 80%?
- [ ] Any unclassified components? → candidates for new trait or transversal pattern
- [ ] Are detection signals still producing accurate results? Check for false positives and negatives
- [ ] Do the +/- examples in each trait section reflect current project patterns?
- [ ] Are any transversal patterns missing? (e.g., drag-and-drop, real-time updates, infinite scroll)

---

## Criteria for Adding a New Trait

1. ≥ 3 components from the crash test sample are unclassifiable by existing traits
2. The pattern is recurring (not a one-off edge case)
3. The trait has test patterns distinct from the existing 5 traits
4. The trait can be expressed as a Gherkin template with ≥ 2 concrete scenarios

**Process:**
1. Draft the new trait definition following the format in `ui-behavioral-taxonomy.md` section 3
2. Run a mini crash test on the unclassified components using the draft trait
3. Verify ≥ 80% classification of the previously unclassified components
4. Bump taxonomy version (v1.0.0 → v1.1.0 for new trait, v2.0.0 if breaking change)
5. Update all command files that reference the taxonomy

---

## Criteria for Modifying an Existing Trait

1. **False positives detected** — injection occurring in non-UI contexts (check EC-001 detection examples)
2. **False negatives detected** — injection missed on clearly UI components
3. **New detection signals identified** — common keywords not yet in the signals table
4. **Gherkin template gaps** — real test scenarios not covered by the template

**Process:**
1. Update the affected trait section in `ui-behavioral-taxonomy.md`
2. Add examples to the Detection examples block (✅/❌) illustrating the fix
3. Bump patch version (v1.0.0 → v1.0.1)
4. Add entry to the `## Changelog` section

---

## Criteria for Deprecating a Trait

1. < 5% of components in recent crash test samples match the trait
2. The trait's test patterns are fully covered by other traits

**Process:**
1. Move trait to a `## Deprecated Traits` section (do not delete — specs may reference it)
2. Add deprecation notice with date and replacement recommendation
3. Bump minor version (v1.0.0 → v1.1.0)

---

## Handling New UI Patterns

When new UI patterns emerge that don't fit existing traits (e.g., drag-and-drop, WebSocket real-time updates, infinite scroll):

1. Document the pattern as an "observed but unclassified" component in the crash test report
2. If the pattern appears in ≥ 3 components in the next quarterly review → trigger "Adding a New Trait" process
3. In the interim, manually write behavioral AC for these components (no injection)

---

## Version Bump Guide

| Change type | Version bump | Example |
|-------------|-------------|---------|
| New trait added | Minor (x.Y.0) | v1.0.0 → v1.1.0 |
| Detection signal or example added | Patch (x.y.Z) | v1.0.0 → v1.0.1 |
| Gherkin template updated | Patch (x.y.Z) | v1.0.0 → v1.0.1 |
| Trait removed or renamed | Major (X.0.0) | v1.0.0 → v2.0.0 |
| Transversal pattern added | Patch (x.y.Z) | v1.0.0 → v1.0.1 |

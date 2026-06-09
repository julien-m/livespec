<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-011) -->
<!-- @spec(FR-009) -->
<!-- @spec(FR-011) -->

# Crash Test Procedure — Behavioral Taxonomy Validation

<!-- @spec AC-011: Crash test procedure — .specs/features/005.1-behavioral-tdd-audit/spec.md#ac-011 -->
<!-- @spec FR-011: Crash test procedure doc — .specs/features/005.1-behavioral-tdd-audit/spec.md#fr-011 -->

**Objective:** Validate that the behavioral taxonomy maps to real-world UI components with a classification rate of at least 80%.

**Taxonomy source of truth:** `system/testing/ui-behavioral-taxonomy.md`

> **Important (EC-001):** Re-read the taxonomy document before each crash test execution. Trait names, detection signals, or test patterns may have been renamed or removed since the last execution.

---

## 1. Sample Selection

Select a minimum of 10 diverse UI components from at least 2 real projects. The sample must include components with user interaction -- pure layout or navigation components are intentionally outside the taxonomy scope.

**Selection criteria:**

| Category | Count | Candidate Traits |
|----------|-------|-----------------|
| Forms with submit buttons | 2-3 | is_submittable, has_validation |
| Async actions (search, file upload, API calls) | 2-3 | async_action |
| Overlays (modals, drawers, dialogs) | 2-3 | has_overlay, dismissible_layer |
| Validation-heavy inputs | 1-2 | has_validation |
| Edge cases (date pickers, autocomplete, etc.) | 1-2 | varies |

**Exclusions:** Components that are purely presentational (static text, icons, layout wrappers) or purely navigational (sidebar, breadcrumbs) are excluded from the sample since they are intentionally outside the behavioral taxonomy scope.

---

## 2. Classification Process

For each component in the sample:

1. **Read component source** (or spec/description if no source is available).
2. **Manual trait detection** -- determine which traits apply from the taxonomy:
   - `is_submittable` -- has a submit button, success/disabled states, submits data
   - `async_action` -- triggers a network request or long-running operation
   - `has_overlay` -- renders above the normal flow (modal, drawer, sheet, popover)
   - `dismissible_layer` -- can be closed by user action (close button, backdrop click, Escape key)
   - `has_validation` -- validates user input, shows error messages
3. **Automated detection** (optional) -- apply `detect_traits(description)` from `validator/taxonomy.py` and compare results with manual detection.
4. **Record results** -- component name, file path, description, matched traits, transversal patterns.
5. **Unclassified components** -- if a component matches zero traits, record it as unclassified with a justification explaining why it falls outside the taxonomy scope (or propose a candidate new trait).

---

## 3. Report Format

Save the report to `.specs/features/005-ui-behavioral-testing/checks/crash-test-YYYY-MM-DD.md` using the following structure:

### Header

```markdown
# Crash Test Report — UI Behavioral Taxonomy

**Date:** YYYY-MM-DD
**Feature:** 005-ui-behavioral-testing
**Sample source:** [project name(s) and component directory path(s)]
**Sample size:** N components
```

### Component-to-Trait Mapping Table

```markdown
## Component -> Trait Mapping

| # | Component | Project | File | Description | Traits Matched | Patterns |
|---|-----------|---------|------|-------------|----------------|----------|
| 1 | ComponentName | project | path/to/file.tsx | Brief description | trait1, trait2 | pattern1 |
```

### Trait Frequency Table

```markdown
## Trait Frequency

| Trait | Count | % of sample |
|-------|-------|-------------|
| is_submittable | N | X% |
| async_action | N | X% |
| has_overlay | N | X% |
| dismissible_layer | N | X% |
| has_validation | N | X% |
```

### Transversal Pattern Frequency Table

```markdown
## Transversal Pattern Frequency

| Pattern | Count | Components |
|---------|-------|------------|
| form-in-modal | N | ComponentA, ComponentB |
| inline-edit | N | ComponentC |
| async-search-select | N | ComponentD |
```

### Unclassified Components

```markdown
## Unclassified Components

List any components that matched zero traits, with justification:
- ComponentName — Justification: [why it falls outside taxonomy scope]
- ComponentName — Candidate trait: `has_X` (if taxonomy expansion is warranted)
```

### Summary and Recommendation

```markdown
## Summary

- Components analyzed: N
- Classified: X/N (Y%)
- Unclassified: Z/N
- Taxonomy adequacy: Adequate (>= 80%) / Needs expansion (< 80%)

## Recommendation

[Based on results: whether taxonomy is adequate for production or needs expansion,
and what traits to add if classification rate is below 80%]
```

---

## 4. Taxonomy Reference

- All classification uses `system/testing/ui-behavioral-taxonomy.md` as the single source of truth.
- The automated detection function is `detect_traits()` in `validator/taxonomy.py`.
- Re-read the taxonomy before each execution to account for any renamed or removed traits (EC-001).
- The report file must be saved to `.specs/features/005-ui-behavioral-testing/checks/crash-test-YYYY-MM-DD.md`.

---

*Procedure defined for Feature 005-ui-behavioral-testing — taxonomy crash test validation.*

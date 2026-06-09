<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-012) -->
<!-- @spec(AC-013) -->
<!-- @spec(FR-009) -->

# Crash Test Report — UI Behavioral Taxonomy

<!-- @spec FR-009: Crash test on real components — .specs/features/005-ui-behavioral-testing/spec.md#fr-009 -->

**Date:** 2026-04-14
**Feature:** 005-ui-behavioral-testing
**Sample source:** projectatlas (`/Users/julienm/projects/projectatlas/src/components/`) + claude-pilot (`/Users/julienm/projects/claude-pilot/src/components/`)
**Sample size:** 13 components

---

## Component -> Trait Mapping

| # | Component | Project | File | Description | Traits Matched | Patterns |
|---|-----------|---------|------|-------------|----------------|----------|
| 1 | AddResourceForm | projectatlas | `components/AddResourceForm.tsx` | Form with inputs, select, validation, submit (uses Loader2 for async icon refresh) | is_submittable, has_validation, async_action | inline-edit |
| 2 | AiResourceImportModal | projectatlas | `components/AiResourceImportModal.tsx` | Dialog modal for AI-powered batch import with textarea input and async LLM call | has_overlay, dismissible_layer, async_action, is_submittable | form-in-modal |
| 3 | EditResourceForm | projectatlas | `components/EditResourceForm.tsx` | Inline edit form with validation, select, input fields | is_submittable, has_validation | inline-edit |
| 4 | SearchInput | projectatlas | `components/SearchInput.tsx` | Search input with clear button, keyboard handling | has_validation | -- |
| 5 | ResourceDrawer | projectatlas | `components/ResourceDrawer.tsx` | Sheet/drawer displaying resource details with add/edit/delete actions | has_overlay, dismissible_layer | -- |
| 6 | AiFillButton | projectatlas | `components/tool/AiFillButton.tsx` | Button triggering async AI call with loading state and toast feedback | async_action | -- |
| 7 | AiSuggestModal | projectatlas | `components/tool/AiSuggestModal.tsx` | Modal displaying AI suggestions with apply/reject actions | has_overlay, dismissible_layer | -- |
| 8 | CapabilitySelector | projectatlas | `components/tool/CapabilitySelector.tsx` | Sheet-based multi-select with tree navigation | has_overlay, dismissible_layer | -- |
| 9 | RadialMinimap | projectatlas | `components/RadialMinimap.tsx` | SVG radial visualization minimap with pan/zoom | -- | -- |
| 10 | Sidebar | projectatlas | `components/Sidebar.tsx` | Static navigation sidebar with view switching | -- | -- |
| 11 | ScheduleForm | claude-pilot | `components/ScheduleForm.tsx` | Form for creating/editing workflow schedules with validation | is_submittable, has_validation, async_action | inline-edit |
| 12 | ScheduledWorkflows | claude-pilot | `components/ScheduledWorkflows.tsx` | Dashboard with table, dialog for edit, switch for enable/disable, async mutations | has_overlay, dismissible_layer, async_action, is_submittable | form-in-modal |
| 13 | ScheduleHistory | claude-pilot | `components/ScheduleHistory.tsx` | Dialog modal with table, filtering, async data fetch | has_overlay, dismissible_layer, async_action | -- |

---

## Trait Frequency

| Trait | Count | % of sample |
|-------|-------|-------------|
| is_submittable | 5 | 38% |
| async_action | 6 | 46% |
| has_overlay | 6 | 46% |
| dismissible_layer | 6 | 46% |
| has_validation | 4 | 31% |

---

## Transversal Pattern Frequency

| Pattern | Count | Components |
|---------|-------|------------|
| form-in-modal | 2 | AiResourceImportModal, ScheduledWorkflows |
| inline-edit | 3 | AddResourceForm, EditResourceForm, ScheduleForm |
| async-search-select | 0 | -- |

---

## Unclassified Components

| Component | Behavioral Characteristic | Taxonomy Gap? |
|-----------|--------------------------|---------------|
| RadialMinimap | Interactive SVG visualization with pan/zoom/hover — pure rendering, no data mutation | No — visualization-only components are intentionally outside behavioral taxonomy scope. The taxonomy targets data-mutating or user-input components. |
| Sidebar | Static navigation — click to switch views, no data mutation, no async, no overlay | No — pure navigation is correctly outside scope. |

---

## Classification Rate

**Classified:** 11/13 (84.6%) — exceeds 80% threshold (SC-001)

---

## Recommendation

**Taxonomy adequate.** The 5 defined traits + 3 transversal patterns cover 84.6% of the real-world component sample. The 2 unclassified components (RadialMinimap, Sidebar) are intentionally outside the taxonomy's scope — they are either pure visualization or pure navigation with no behavioral patterns that would benefit from automated testing injection.

**Observations:**
- `async_action` and overlay traits (`has_overlay` + `dismissible_layer`) are the most common, appearing in nearly half the sample
- The `async-search-select` transversal pattern had no matches in this sample, but remains valid for projects with async dropdown/combobox patterns
- `SearchInput` exhibits lightweight validation (`has_validation`) but does not trigger async search — it is a controlled input with clear, not a full async-search-select
- No new traits or patterns are recommended at this time

---

*Generated by livespec crash test procedure — 2026-04-14*

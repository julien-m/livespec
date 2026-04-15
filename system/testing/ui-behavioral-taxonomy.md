# UI Behavioral Taxonomy

<!-- @spec FR-001: Behavioral taxonomy source of truth — .specs/features/005-ui-behavioral-testing/spec.md#fr-001 -->

> Single source of truth for UI behavioral trait definitions, Gherkin templates, and test patterns.
> Referenced by `/spec.specify`, `/spec.implement`, and `/spec.test`. No command file may duplicate trait definitions — all must defer to this document.

**Version:** 2026-04-14
**Taxonomy Version:** v1.0.0
**Feature:** 005-ui-behavioral-testing

---

## 1. Purpose

This document defines the behavioral traits that UI components exhibit. Commands use this taxonomy to:

- **`/spec.specify`** — detect traits in feature descriptions and inject Gherkin AC
- **`/spec.implement`** — drive TDD with trait-specific test patterns (RED phase)
- **`/spec.test`** — audit existing test files for behavioral coverage gaps

---

## 2. Traits Summary

| Trait | Description | Typical components |
|-------|-------------|--------------------|
| `is_submittable` | Can be submitted by the user (form, action) | Forms, save buttons, send buttons |
| `async_action` | Triggers an asynchronous operation | API calls, file uploads, search |
| `has_overlay` | Renders above other content | Modals, dialogs, drawers, popovers |
| `dismissible_layer` | Can be closed/dismissed by the user | Modals, drawers, tooltips, toasts |
| `has_validation` | Validates user input before proceeding | Form fields, inline editors, search filters |

---

## 3. Trait Definitions

### is_submittable

**Description:** Component contains a user-initiated action that submits data or triggers a state change (form submission, save, send, create).

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "submit button" | Sufficient alone (unambiguous UI) |
| "form" | Sufficient alone (unambiguous UI) |
| "save" | Requires at least 1 other UI signal |
| "send" | Requires at least 1 other UI signal |
| "create" (with entity) | Requires UI context (e.g., "create dialog", "create form") |

**Detection examples:**

✅ **INJECT** (positive examples):
- "form with submit button and validation" → `is_submittable` + `has_validation`
- "create user dialog with save button" → `is_submittable` (dialog = unambiguous UI context)
- "modal with form and async submit" → `is_submittable` + `async_action` + `has_overlay`

❌ **DO NOT INJECT** (EC-001 — no UI context):
- "submit a report to the analytics server" → backend operation, no UI signal
- "save configuration to database" → no UI signal, pure backend
- "send notification email" → backend action, not user-initiated UI submit

**Ambiguous cases (requires ≥2 signals):**
- "save settings" alone → ❌ insufficient (could be backend)
- "save settings button in preferences dialog" → ✅ sufficient (dialog + button = UI context)

**Gherkin template:**

```gherkin
Scenario: Submit with valid data
  Given the user has filled all required fields
  When the user clicks the submit/save button
  Then the data is persisted
  And a success confirmation is displayed

Scenario: Submit with empty required fields
  Given the user has not filled required fields
  When the user clicks the submit/save button
  Then submission is prevented
  And required field errors are displayed

Scenario: Submit button disabled state
  Given the form is in an invalid state
  Then the submit button is disabled or visually indicates unavailability
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Submit success | `submit-success` | Submit with valid data persists and confirms |
| Submit validation block | `submit-disabled` | Submit prevented when required fields empty |
| Submit disabled state | `submit-disabled-state` | Button disabled or visually unavailable when invalid |

---

### async_action

**Description:** Component triggers an operation that is not instantaneous — network request, file upload, long computation. Requires loading state, double-click prevention, and error/retry handling.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "loading" | Sufficient alone |
| "spinner" | Sufficient alone |
| "network request" | Sufficient alone |
| "API call" | Sufficient alone |
| "fetch" | Requires UI context (not backend fetch) |
| "long operation" | Sufficient alone |
| "file upload" | Sufficient alone |

**Detection examples:**

✅ **INJECT** (positive examples):
- "search button with spinner during API call" → `async_action`
- "file upload with progress indicator" → `async_action`
- "submit button that fetches results with loading state" → `async_action` + `is_submittable`

❌ **DO NOT INJECT** (EC-001 — no UI context):
- "backend service that fetches data from database" → no UI, pure backend fetch
- "cron job that runs a long operation" → no UI trigger
- "API endpoint that processes a file upload" → server-side, no UI component

**Ambiguous cases (requires ≥2 signals):**
- "fetch data" alone → ❌ insufficient (backend fetch likely)
- "fetch data when button clicked" → ✅ sufficient (button = UI trigger)

**Gherkin template:**

```gherkin
Scenario: Loading state during async operation
  Given the user triggers the async action
  When the operation is in progress
  Then a loading indicator is visible
  And the trigger element indicates busy state

Scenario: Double-click prevention
  Given the user triggers the async action
  When the user clicks the trigger again before completion
  Then only one operation is dispatched
  And the trigger is disabled during execution

Scenario: Error and retry on failure
  Given the async action has failed
  Then an error message is displayed
  And a retry option is available
  When the user retries
  Then the operation is re-dispatched
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Loading state | `loading-state` | Loading indicator visible during operation |
| Double-click prevention | `double-click` | Only one operation dispatched on rapid clicks |
| Error and retry | `error-retry` | Error displayed with retry option after failure |

---

### has_overlay

**Description:** Component renders content above the normal document flow — visually overlays existing content with a backdrop or layered surface.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "modal" | Sufficient alone (unambiguous UI) |
| "dialog" | Sufficient alone (unambiguous UI) |
| "drawer" | Sufficient alone (unambiguous UI) |
| "overlay" | Sufficient alone |
| "popup" | Sufficient alone |
| "popover" | Sufficient alone |
| "sheet" | Requires UI context |

**Detection examples:**

✅ **INJECT** (positive examples):
- "confirmation modal" → `has_overlay` + `dismissible_layer`
- "settings drawer that slides in from the right" → `has_overlay` + `dismissible_layer`
- "delete confirmation dialog" → `has_overlay` + `dismissible_layer`

❌ **DO NOT INJECT** (EC-001 — no overlay):
- "inline settings panel on the page" → page-level, not overlaid
- "expandable accordion section" → no overlay, inline content
- "tooltip on hover" → typically not a full overlay requiring focus trap / scroll lock

**Ambiguous cases (requires ≥2 signals):**
- "sheet" alone → ❌ ambiguous (could be spreadsheet)
- "bottom sheet with dismiss button" → ✅ sufficient (dismiss + overlay context)

**Gherkin template:**

```gherkin
Scenario: Overlay renders above page content
  Given the page has existing content
  When the overlay is triggered
  Then the overlay renders above the page content
  And a backdrop or scrim is visible behind the overlay

Scenario: Focus is trapped inside overlay
  Given the overlay is open
  When the user navigates with Tab key
  Then focus cycles within the overlay
  And does not reach page content behind the overlay

Scenario: Body scroll is locked when overlay is open
  Given the overlay is open
  Then the page body does not scroll
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Overlay rendering | `overlay-render` | Overlay visible above page content |
| Focus trap | `focus-trap` | Tab navigation stays inside overlay |
| Scroll lock | `scroll-lock` | Body scroll disabled when overlay open |

---

### dismissible_layer

**Description:** Component can be closed or dismissed by the user through explicit actions (close button, Escape key) or implicit actions (click outside).

> **Note:** `dismissible_layer` almost always co-occurs with `has_overlay`. If `has_overlay` is detected, `dismissible_layer` should be checked as well.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "close button" | Sufficient alone |
| "dismiss" | Sufficient alone |
| "escape key" | Sufficient alone |
| "click outside" | Sufficient alone |
| "closable" | Sufficient alone |

**Detection examples:**

✅ **INJECT** (positive examples):
- "modal with close button" → `dismissible_layer` + `has_overlay`
- "dialog closable via Escape key" → `dismissible_layer`
- "drawer that closes on click outside" → `dismissible_layer` + `has_overlay`

❌ **DO NOT INJECT** (EC-001 — no dismissible UI layer):
- "user can close their account" → account action, not a UI layer
- "administrator dismisses a notification from the admin panel" → UI action but no layer component
- "session expires and closes the connection" → system event, not user-dismissible layer

**Ambiguous cases (requires ≥2 signals):**
- "closable" alone → ❌ ambiguous (could describe any closable thing)
- "closable notification panel with X button" → ✅ sufficient (panel + button = dismissible layer)

**Gherkin template:**

```gherkin
Scenario: Dismiss via close button
  Given the layer is open
  When the user clicks the close button
  Then the layer is removed from view
  And focus returns to the trigger element

Scenario: Dismiss via Escape key
  Given the layer is open
  When the user presses the Escape key
  Then the layer is removed from view

Scenario: Dismiss via click outside
  Given the layer is open
  When the user clicks outside the layer
  Then the layer is removed from view
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Close button | `close-button` | Layer closes on close button click |
| Escape key | `escape-dismiss` | Layer closes on Escape key press |
| Click outside | `click-outside` | Layer closes on outside click |

---

### has_validation

**Description:** Component validates user input before allowing progression — required fields, format checks, constraint enforcement, and inline error display.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "validation" | Sufficient alone |
| "error message" | Requires form/input context |
| "required field" | Sufficient alone |
| "format check" | Sufficient alone |
| "field error" | Sufficient alone |
| "inline error" | Sufficient alone |

**Detection examples:**

✅ **INJECT** (positive examples):
- "form with email validation and required fields" → `has_validation` + `is_submittable`
- "input that shows inline error when format is invalid" → `has_validation`
- "password field with strength requirements" → `has_validation`

❌ **DO NOT INJECT** (EC-001 — no UI validation):
- "server validates the JWT token on each request" → server-side validation, no UI
- "database constraint prevents duplicate emails" → DB-level, no UI component
- "API returns 422 when required fields are missing" → backend validation response

**Ambiguous cases (requires ≥2 signals):**
- "error message" alone → ❌ ambiguous (could be a system error, not form validation)
- "error message shown below the input field" → ✅ sufficient (input + error = UI validation)

**Gherkin template:**

```gherkin
Scenario: Required field validation
  Given the user has left a required field empty
  When the user attempts to proceed
  Then an error message is displayed for the empty field
  And the field is visually marked as invalid

Scenario: Format validation
  Given the user has entered data in an invalid format
  When the field loses focus or the user attempts to proceed
  Then a format error message is displayed
  And the message describes the expected format

Scenario: Error clears on correction
  Given a field is showing a validation error
  When the user corrects the input
  Then the error message is removed
  And the field returns to a valid visual state
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Required field | `required-field` | Error shown for empty required fields |
| Format validation | `format-validation` | Error shown for invalid format |
| Error clearance | `error-clearance` | Error removed after correction |

---

## 4. Transversal Patterns

Transversal patterns are combinations of traits that frequently co-occur. When a component matches a transversal pattern, all constituent traits are applied (with deduplication per section 5).

### form-in-modal

**Constituent traits:** `is_submittable` + `has_overlay` + `dismissible_layer`

**Disambiguation:** Apply when a form is presented inside a modal, dialog, or drawer. Do not apply if the form is inline on a page.

**Combined Gherkin template:**

```gherkin
Scenario: Form submits from within modal
  Given the modal is open with a form
  When the user fills required fields and submits
  Then the data is persisted
  And the modal closes after successful submission

Scenario: Unsaved changes warning on dismiss
  Given the modal form has unsaved changes
  When the user attempts to dismiss (close/escape/click outside)
  Then a confirmation prompt warns about unsaved changes

Scenario: Modal closes cleanly on cancel
  Given the modal is open
  When the user clicks cancel or dismiss without changes
  Then the modal closes without persistence
  And no error is displayed
```

### inline-edit

**Constituent traits:** `is_submittable` + `has_validation`

**Disambiguation:** Apply when a value is edited in-place (click-to-edit, inline input). Do not apply if the edit happens in a separate form/page.

**Combined Gherkin template:**

```gherkin
Scenario: Inline edit saves on confirm
  Given the user activates inline edit on a field
  When the user modifies the value and confirms (Enter/blur)
  Then the new value is persisted
  And the field returns to display mode

Scenario: Inline edit validates before save
  Given the user activates inline edit
  When the user enters an invalid value and confirms
  Then the value is not saved
  And a validation error is displayed inline

Scenario: Inline edit cancels on Escape
  Given the user is editing a field inline
  When the user presses Escape
  Then the original value is restored
  And the field returns to display mode
```

### async-search-select

**Constituent traits:** `async_action` + `has_validation`

**Disambiguation:** Apply when a search/select input fetches results asynchronously. Do not apply to simple static dropdowns.

**Combined Gherkin template:**

```gherkin
Scenario: Search triggers async fetch
  Given the user types in the search input
  When at least N characters are entered (debounced)
  Then results are fetched asynchronously
  And a loading indicator appears during fetch

Scenario: No results state
  Given the user searches for a term with no matches
  Then an empty state message is displayed
  And the user can modify their search

Scenario: Selection validates against constraints
  Given the user selects a result
  When the selection violates a constraint (e.g., max items)
  Then a validation error is displayed
  And the selection is not applied
```

---

## 5. Deduplication Rule

This section is the authoritative statement of the deduplication rule. All other references in command files must point here rather than restating the rule.

### EC-004: Multiple pattern matches

When a component matches multiple transversal patterns, all matching patterns are applied. Shared traits between patterns are injected **once** — deduplication is by trait name. For example, a form-in-modal with async submit matches both `form-in-modal` and potentially `async_action`, but `is_submittable` Gherkin is injected only once.

### EC-002: Overlap with manually written AC

When `## Behavioral AC` contains trait-based Gherkin and `## Acceptance Criteria` contains manually written scenarios covering the same behavior:

1. The `## Behavioral AC` section is **authoritative** for behavioral patterns
2. `/spec.implement` merges overlapping scenarios into a single test, referencing both AC IDs (e.g., "AC-003 / Behavioral-async_action: loading state")
3. No duplicate tests are generated for the same behavior

---

## 6. Error Handling

### EC-005: Missing taxonomy — asymmetric behavior

Commands handle a missing taxonomy document differently by design:

| Command | Behavior when taxonomy is missing | Rationale |
|---------|----------------------------------|-----------|
| `/spec.specify` | **Fail fast** with: "Behavioral taxonomy not found at system/testing/ui-behavioral-taxonomy.md. Run /spec.specify --no-behavioral or create the taxonomy first." | Injection requires the taxonomy to produce correct Gherkin. Injecting without it would produce incorrect or incomplete behavioral AC. |
| `/spec.implement` | **Degrade gracefully** — skip behavioral TDD step with WARNING: "Behavioral AC declared but taxonomy not found. Behavioral TDD step will be skipped." | Implementation can proceed without behavioral TDD. The behavioral tests are additive quality, not blocking. |
| `/spec.test` | **Degrade gracefully** — skip behavioral audit with WARNING | Audit is additive. Missing taxonomy does not invalidate structural test coverage. |

This asymmetry is intentional: `/spec.specify` is the injection point where incorrect data would propagate downstream. `/spec.implement` and `/spec.test` are consumers that can function without behavioral data.

---

---

## 7. Changelog

### v1.0.0 (2026-04-14)
- Initial taxonomy: 5 traits (is_submittable, async_action, has_overlay, dismissible_layer, has_validation)
- 3 transversal patterns (form-in-modal, inline-edit, async-search-select)
- Crash test: 84.6% coverage on 13 real-world components
- Deduplication rules (EC-002, EC-004)
- Asymmetric error handling (EC-005)

---

*Generated by livespec — 2026-04-14*

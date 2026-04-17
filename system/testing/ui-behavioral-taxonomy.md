# UI Behavioral Taxonomy

<!-- @spec FR-001: Behavioral taxonomy source of truth — .specs/features/005-ui-behavioral-testing/spec.md#fr-001 -->

> Single source of truth for UI behavioral trait definitions, Gherkin templates, and test patterns.
> Referenced by `/spec.specify`, `/spec.implement`, and `/spec.test`. No command file may duplicate trait definitions — all must defer to this document.

**Version:** 2026-04-17
**Taxonomy Version:** v2.0.0
**Feature:** 005-ui-behavioral-testing, 005.2-taxonomy-complete-expansion

---

## 1. Purpose

This document defines the behavioral traits that UI components exhibit. Commands use this taxonomy to:

- **`/spec.specify`** — detect traits in feature descriptions and inject Gherkin AC
- **`/spec.implement`** — drive TDD with trait-specific test patterns (RED phase)
- **`/spec.test`** — audit existing test files for behavioral coverage gaps

---

## 2. Traits Summary

| Trait | Category | Description | Typical components |
|-------|----------|-------------|--------------------|
| `is_submittable` | Core | Can be submitted by the user (form, action) | Forms, save buttons, send buttons |
| `async_action` | Core | Triggers an asynchronous operation | API calls, file uploads, search |
| `has_overlay` | Core | Renders above other content | Modals, dialogs, drawers, popovers |
| `dismissible_layer` | Core | Can be closed/dismissed by the user | Modals, drawers, tooltips, toasts |
| `has_validation` | Core | Validates user input before proceeding | Form fields, inline editors, search filters |
| `is_navigable` | Navigation & Layout | Navigation between pages/views/states | Tabs, steppers, breadcrumbs |
| `has_dropdown` | Navigation & Layout | Dropdown menu (non-modal) | Dropdowns, selects, comboboxes |
| `is_collapsible` | Navigation & Layout | Content expand/collapse | Accordions, expandable sections |
| `has_pagination` | Navigation & Layout | Multi-page data navigation | Paginators, load-more buttons |
| `is_sortable` | Data Display | Data sortable by criteria | Sortable table columns |
| `is_filterable` | Data Display | Data filterable by criteria | Filter bars, faceted search |
| `has_selection` | Data Display | Item selection (single/multi) | Checkbox lists, multi-selects |
| `shows_notification` | User Feedback | Toast/banner/alert messages | Toasts, snackbars, banners |
| `has_confirmation` | User Feedback | Confirmation dialog before action | Delete confirmations, destructive action gates |
| `has_progress_indicator` | User Feedback | Multi-step progress display | Progress bars, wizards, steppers |
| `has_tooltip` | User Feedback | Info bubble on hover/focus | Tooltips, help icons |
| `has_drag_drop` | Advanced Interactions | Drag-and-drop support | Kanban boards, reorderable lists |
| `has_dirty_state` | Advanced Interactions | Detects unsaved changes | Edit forms, settings panels |
| `is_optimistic` | Advanced Interactions | UI updates before server confirm | Like buttons, inline edits |
| `is_keyboard_navigable` | Advanced Interactions | Full keyboard navigation | Accessible components, shortcut-driven UIs |
| `has_date_picker` | Specialized Components | Date/time selection widget | Date pickers, calendar widgets |
| `has_rich_text` | Specialized Components | WYSIWYG text editor | Rich text editors, markdown editors |

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

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| disabled | `[disabled]`, `.btn-disabled`, `aria-disabled="true"` | submit-disabled.png |
| enabled | `:not([disabled])`, `.btn-primary` | submit-enabled.png |
| loading | `[aria-busy="true"]`, `.btn-loading` | submit-loading.png |

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

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| idle | (none) | async-idle.png |
| loading | `[aria-busy="true"]`, `.loading-spinner` | async-loading.png |
| error | `.error-state`, `[data-error]` | async-error.png |
| success | `.success-state`, `[data-success]` | async-success.png |

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

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| closed | `.modal[aria-hidden="true"]`, `display:none` | overlay-closed.png |
| open | `.modal[aria-hidden="false"]`, `.backdrop` | overlay-open.png |
| focused | `.modal:focus-within` | overlay-focused.png |

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

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| open | `.layer[aria-hidden="false"]` | dismissible-open.png |
| closing | `.layer-exit`, `.layer-exit-active` | dismissible-closing.png |
| closed | `.layer[aria-hidden="true"]` | dismissible-closed.png |

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

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| valid | `.field-valid`, `[aria-invalid="false"]` | validation-valid.png |
| invalid | `.field-invalid`, `[aria-invalid="true"]` | validation-invalid.png |
| empty | `.field-empty`, `:placeholder-shown` | validation-empty.png |

---

<!-- @spec FR-001: 17 new trait definitions — .specs/features/005.2-taxonomy-complete-expansion/spec.md#fr-001 -->

### is_navigable

**Description:** Component enables navigation between pages, views, or states — tabs, steppers, breadcrumbs, or paginated views with active state indication.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "tabs" | Sufficient alone (unambiguous UI) |
| "pagination" | Sufficient alone (unambiguous UI) |
| "stepper" | Sufficient alone (unambiguous UI) |
| "breadcrumb" | Sufficient alone (unambiguous UI) |
| "page navigation" | Requires UI context |

**Detection examples:**

INJECT (positive examples):
- "tabs with URL state preservation" -> `is_navigable`
- "multi-step wizard with stepper" -> `is_navigable` + `has_progress_indicator`
- "breadcrumb navigation in settings" -> `is_navigable`

DO NOT INJECT (EC-001 -- no UI context):
- "navigate the codebase to find the bug" -> developer action, not UI navigation
- "page through log entries in the terminal" -> CLI context, not UI tabs

**Ambiguous cases (requires >=2 signals):**
- "page navigation" alone -> ambiguous (could be backend pagination)
- "page navigation with active tab indicator" -> sufficient (tab + navigation = UI)

**Gherkin template:**

```gherkin
Scenario: Tab navigation updates active state
  Given a tab bar with multiple tabs
  When the user clicks a tab
  Then the clicked tab becomes active
  And the previous tab becomes inactive

Scenario: Navigation syncs with URL
  Given the user navigates to a tab
  When the URL is updated
  Then refreshing the page restores the active tab
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Tab navigation | `tab-navigation` | Active tab changes on click |
| URL state | `url-state` | URL reflects current navigation state |
| Active indicator | `active-indicator` | Visual indicator marks the active item |

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| inactive | `.tab:not(.active)`, `[aria-selected="false"]` | navigable-inactive.png |
| active | `.tab.active`, `[aria-selected="true"]` | navigable-active.png |
| hover | `.tab:hover` | navigable-hover.png |

---

### has_dropdown

**Description:** Component displays a dropdown menu (non-modal) for selecting options or triggering actions. Distinct from `has_overlay` in that dropdowns are lightweight and do not trap focus.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "dropdown" | Sufficient alone (unambiguous UI) |
| "select" | Requires form context |
| "combobox" | Sufficient alone (unambiguous UI) |
| "menu" | Requires non-modal context |

**Detection examples:**

INJECT (positive examples):
- "dropdown menu for category selection" -> `has_dropdown`
- "combobox with autocomplete" -> `has_dropdown`
- "select input in a form" -> `has_dropdown` (form context present)

DO NOT INJECT (EC-001 -- no UI context):
- "select the database engine for deployment" -> infrastructure choice, not UI dropdown
- "menu of API endpoints in the docs" -> documentation structure, not interactive dropdown

**Ambiguous cases (requires >=2 signals):**
- "select" alone -> ambiguous (could be SQL SELECT)
- "select field in the registration form" -> sufficient (form + select = UI dropdown)

**Gherkin template:**

```gherkin
Scenario: Dropdown opens on trigger click
  Given a dropdown trigger button
  When the user clicks the trigger
  Then the dropdown menu opens
  And options are visible

Scenario: Dropdown closes on selection
  Given the dropdown is open
  When the user selects an option
  Then the dropdown closes
  And the selected value is displayed

Scenario: Dropdown closes on outside click
  Given the dropdown is open
  When the user clicks outside the dropdown
  Then the dropdown closes
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Dropdown open | `dropdown-open` | Dropdown opens on trigger click |
| Dropdown close | `dropdown-close` | Dropdown closes on selection or outside click |
| Dropdown selection | `dropdown-selection` | Selected value updates the trigger display |

---

### is_collapsible

**Description:** Component supports expand/collapse behavior -- content is hidden by default or toggleable by the user (accordions, expandable sections, collapsible panels).

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "accordion" | Sufficient alone (unambiguous UI) |
| "expandable" | Sufficient alone (unambiguous UI) |
| "collapse" | Sufficient alone (unambiguous UI) |
| "details" | Requires expand context |

**Detection examples:**

INJECT (positive examples):
- "expandable FAQ section with accordion" -> `is_collapsible`
- "collapsible sidebar panel" -> `is_collapsible`
- "details/summary for advanced settings" -> `is_collapsible` (expand context present)

DO NOT INJECT (EC-001 -- no UI context):
- "collapse the database indexes for performance" -> database operation, not UI
- "expand the test suite coverage" -> testing context, not UI expand/collapse

**Ambiguous cases (requires >=2 signals):**
- "details" alone -> ambiguous (could mean "detail page")
- "details section that expands on click" -> sufficient (expand context present)

**Gherkin template:**

```gherkin
Scenario: Section expands on header click
  Given a collapsed section
  When the user clicks the section header
  Then the section content becomes visible
  And the expand indicator rotates/changes

Scenario: Section collapses on repeat click
  Given an expanded section
  When the user clicks the section header again
  Then the section content is hidden
  And the expand indicator returns to default state
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Expand collapse | `expand-collapse` | Content toggles visibility on click |
| Toggle state | `toggle-state` | Expand/collapse state is tracked correctly |
| Animation | `animation` | Expand/collapse transition animates smoothly |

---

### has_pagination

**Description:** Component supports multi-page data navigation -- splitting large datasets into discrete pages with navigation controls.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "pagination" | Sufficient alone (unambiguous UI) |
| "page navigation" | Sufficient alone (unambiguous UI) |
| "next/previous" | Requires data context |
| "load more" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "paginated list with 20 items per page" -> `has_pagination`
- "load more button at the bottom of the feed" -> `has_pagination`
- "next/previous buttons for search results" -> `has_pagination` (data context present)

DO NOT INJECT (EC-001 -- no UI context):
- "paginate the API response with cursor" -> backend pagination, not UI
- "next step in the deployment pipeline" -> pipeline context, not data pagination

**Ambiguous cases (requires >=2 signals):**
- "next/previous" alone -> ambiguous (could be wizard steps)
- "next/previous buttons on the product listing page" -> sufficient (data context present)

**Gherkin template:**

```gherkin
Scenario: Navigate to next page
  Given a paginated list showing page 1
  When the user clicks "Next"
  Then page 2 is displayed
  And the page indicator shows "Page 2"

Scenario: Page indicator displays current position
  Given a paginated list with 10 pages
  When the user navigates to page 5
  Then the page indicator shows "Page 5 of 10"
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Page navigation | `page-navigation` | User can navigate between pages |
| Page indicator | `page-indicator` | Current page position is displayed |
| Items per page | `items-per-page` | Correct number of items shown per page |

---

### is_sortable

**Description:** Component allows data to be sorted by one or more criteria -- column headers in tables, sort controls in lists.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "sortable" | Sufficient alone (unambiguous UI) |
| "sort by column" | Sufficient alone (unambiguous UI) |
| "sort order" | Sufficient alone (unambiguous UI) |
| "column header click" | Requires table context |

**Detection examples:**

INJECT (positive examples):
- "table with sortable columns" -> `is_sortable`
- "sort by name, date, or price" -> `is_sortable`
- "column header click toggles sort order" -> `is_sortable` (table context present)

DO NOT INJECT (EC-001 -- no UI context):
- "sort the database results by timestamp" -> backend query, not UI sorting
- "sort the configuration keys alphabetically" -> config processing, not UI

**Ambiguous cases (requires >=2 signals):**
- "column header click" alone -> ambiguous (could be column selection)
- "column header click sorts the table ascending" -> sufficient (table context present)

**Gherkin template:**

```gherkin
Scenario: Click column to sort ascending
  Given a table with unsorted data
  When the user clicks a column header
  Then the data is sorted ascending by that column
  And a sort indicator shows ascending direction

Scenario: Click again to sort descending
  Given the table is sorted ascending by a column
  When the user clicks the same column header
  Then the data is sorted descending
  And the sort indicator shows descending direction
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Column sort | `column-sort` | Clicking column header sorts data |
| Sort toggle | `sort-toggle` | Repeated clicks toggle asc/desc/none |
| Sort indicator | `sort-indicator` | Visual indicator shows current sort state |

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| unsorted | `.th-sortable` | sortable-unsorted.png |
| ascending | `.th-sortable.sort-asc`, `[aria-sort="ascending"]` | sortable-ascending.png |
| descending | `.th-sortable.sort-desc`, `[aria-sort="descending"]` | sortable-descending.png |

---

### is_filterable

**Description:** Component allows data to be filtered by user-defined criteria -- search inputs, faceted filters, advanced search panels.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "filter" | Requires data context |
| "faceted search" | Sufficient alone (unambiguous UI) |
| "filter by" | Sufficient alone (unambiguous UI) |
| "advanced search" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "filter products by category and price range" -> `is_filterable`
- "faceted search with checkboxes" -> `is_filterable`
- "advanced search panel with multiple criteria" -> `is_filterable`

DO NOT INJECT (EC-001 -- no UI context):
- "filter log entries by severity in the backend" -> server-side filtering, not UI
- "filter spam emails before delivery" -> email processing, not UI

**Ambiguous cases (requires >=2 signals):**
- "filter" alone -> ambiguous (could be backend filter)
- "filter input above the product list" -> sufficient (data context present)

**Gherkin template:**

```gherkin
Scenario: Apply filter reduces results
  Given a list of items
  When the user applies a filter criterion
  Then only matching items are displayed
  And the result count updates

Scenario: Clear filter restores all results
  Given a filtered list
  When the user clears the filter
  Then all items are displayed again
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Filter apply | `filter-apply` | Applying filter reduces visible results |
| Filter clear | `filter-clear` | Clearing filter restores all results |
| Filter state | `filter-state` | Active filters are visually indicated |

---

### has_selection

**Description:** Component supports selecting one or more items from a list -- checkboxes, radio buttons, multi-select, bulk actions.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "select items" | Sufficient alone (unambiguous UI) |
| "checkbox" | Requires list context |
| "multi-select" | Sufficient alone (unambiguous UI) |
| "bulk action" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "table with checkbox selection and bulk delete" -> `has_selection`
- "multi-select dropdown for tags" -> `has_selection`
- "select all items with one click" -> `has_selection`

DO NOT INJECT (EC-001 -- no UI context):
- "select the deployment target from config" -> configuration, not UI selection
- "bulk insert records into the database" -> database operation, not UI

**Ambiguous cases (requires >=2 signals):**
- "checkbox" alone -> ambiguous (could be a single toggle)
- "checkbox on each row of the user table" -> sufficient (list context present)

**Gherkin template:**

```gherkin
Scenario: Select single item
  Given a list of items with selection checkboxes
  When the user checks one item
  Then that item is marked as selected
  And the selection count shows 1

Scenario: Select all with bulk action
  Given a list of items
  When the user clicks "Select All"
  Then all items are selected
  And bulk action buttons are enabled
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Selection single | `selection-single` | Single item can be selected/deselected |
| Selection multi | `selection-multi` | Multiple items can be selected simultaneously |
| Select all | `select-all` | Select-all toggle selects/deselects all items |

---

### shows_notification

**Description:** Component displays transient messages to inform the user about the result of an action -- toasts, snackbars, banners, alerts that appear and optionally auto-dismiss.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "toast" | Sufficient alone (unambiguous UI) |
| "notification" | Requires dismiss context |
| "alert" | Requires transient context |
| "snackbar" | Sufficient alone (unambiguous UI) |
| "banner" | Requires dismissible context |

**Detection examples:**

INJECT (positive examples):
- "success toast after saving" -> `shows_notification`
- "snackbar with undo action" -> `shows_notification`
- "dismissible notification banner at the top" -> `shows_notification` (dismiss context present)

DO NOT INJECT (EC-001 -- no UI context):
- "send a push notification to the user's phone" -> push notification, not UI toast
- "alert the ops team via PagerDuty" -> external alerting, not UI notification

**Ambiguous cases (requires >=2 signals):**
- "notification" alone -> ambiguous (could be push notification)
- "notification toast that auto-dismisses after 5 seconds" -> sufficient (dismiss context present)

**Gherkin template:**

```gherkin
Scenario: Notification appears after action
  Given the user performs a successful action
  Then a notification message is displayed
  And the notification is visible for at least 3 seconds

Scenario: Notification auto-dismisses
  Given a notification is displayed
  When the auto-dismiss timeout elapses
  Then the notification fades out
  And the notification is removed from the DOM
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Notification appear | `notification-appear` | Notification appears after triggering action |
| Notification dismiss | `notification-dismiss` | Notification can be manually dismissed |
| Auto dismiss | `auto-dismiss` | Notification disappears after timeout |

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| hidden | `.toast[aria-hidden="true"]` | notification-hidden.png |
| visible | `.toast[aria-hidden="false"]` | notification-visible.png |
| dismissing | `.toast.exit-active` | notification-dismissing.png |

---

### has_confirmation

**Description:** Component requires user confirmation before executing a destructive or irreversible action -- confirmation dialogs, "are you sure" prompts.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "confirmation" | Sufficient alone (unambiguous UI) |
| "are you sure" | Sufficient alone (unambiguous UI) |
| "confirm delete" | Sufficient alone (unambiguous UI) |
| "destructive action" | Requires confirm pattern |

**Detection examples:**

INJECT (positive examples):
- "confirmation dialog before account deletion" -> `has_confirmation`
- "are you sure you want to discard changes?" -> `has_confirmation`
- "confirm delete button with red warning" -> `has_confirmation`

DO NOT INJECT (EC-001 -- no UI context):
- "confirm the deployment via CI pipeline" -> CI confirmation, not UI
- "destructive migration that drops tables" -> database operation, not UI

**Ambiguous cases (requires >=2 signals):**
- "destructive action" alone -> ambiguous (could be backend)
- "destructive action with confirmation modal" -> sufficient (confirm pattern present)

**Gherkin template:**

```gherkin
Scenario: Confirmation appears before destructive action
  Given the user clicks a destructive action button
  Then a confirmation dialog appears
  And the dialog explains the consequences

Scenario: Cancel aborts the action
  Given the confirmation dialog is shown
  When the user clicks Cancel
  Then the action is not executed
  And the dialog closes
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Confirmation show | `confirmation-show` | Confirmation dialog appears before action |
| Confirmation cancel | `confirmation-cancel` | Canceling returns to previous state |
| Confirmation proceed | `confirmation-proceed` | Confirming executes the action |

---

### has_progress_indicator

**Description:** Component displays progress through a multi-step process -- progress bars, wizards, step indicators that show completion state.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "progress bar" | Sufficient alone (unambiguous UI) |
| "wizard" | Sufficient alone (unambiguous UI) |
| "steps" | Requires multi-step context |
| "stepper" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "3-step wizard with progress bar" -> `has_progress_indicator`
- "onboarding stepper showing 4 steps" -> `has_progress_indicator`
- "file upload progress bar" -> `has_progress_indicator`

DO NOT INJECT (EC-001 -- no UI context):
- "build pipeline steps in CI" -> CI pipeline, not UI progress
- "progress through the queue processing" -> backend processing, not UI

**Ambiguous cases (requires >=2 signals):**
- "steps" alone -> ambiguous (could be recipe steps, documentation steps)
- "steps indicator showing current onboarding step" -> sufficient (multi-step context present)

**Gherkin template:**

```gherkin
Scenario: Progress bar updates on step completion
  Given a multi-step wizard at step 1 of 4
  When the user completes step 1
  Then the progress bar shows 25% complete
  And step 2 becomes active

Scenario: Back button navigates to previous step
  Given the wizard is at step 3
  When the user clicks Back
  Then step 2 is displayed
  And the progress bar updates accordingly
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Progress display | `progress-display` | Progress indicator shows current completion |
| Progress update | `progress-update` | Progress updates on step change |
| Step navigation | `step-navigation` | User can navigate forward and backward |

---

### has_tooltip

**Description:** Component displays an informational bubble on hover or focus -- tooltips, help text popups, info icons with contextual help.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "tooltip" | Sufficient alone (unambiguous UI) |
| "help text" | Requires hover context |
| "hint" | Requires hover context |
| "info icon" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "tooltip on hover showing field description" -> `has_tooltip`
- "info icon with help text popup" -> `has_tooltip`
- "hint text appears when hovering over the label" -> `has_tooltip` (hover context present)

DO NOT INJECT (EC-001 -- no UI context):
- "help text in the README documentation" -> static documentation, not UI tooltip
- "hint in the CLI output for the next command" -> CLI hint, not UI tooltip

**Ambiguous cases (requires >=2 signals):**
- "help text" alone -> ambiguous (could be static text)
- "help text appears on hover over the input label" -> sufficient (hover context present)

**Gherkin template:**

```gherkin
Scenario: Tooltip appears on hover
  Given an element with a tooltip
  When the user hovers over the element
  Then the tooltip text is displayed
  And the tooltip is positioned near the element

Scenario: Tooltip disappears on blur
  Given a tooltip is visible
  When the user moves the mouse away
  Then the tooltip disappears
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Tooltip show | `tooltip-show` | Tooltip appears on hover or focus |
| Tooltip hide | `tooltip-hide` | Tooltip disappears on mouse leave or blur |
| Tooltip position | `tooltip-position` | Tooltip positioned correctly relative to trigger |

---

### has_drag_drop

**Description:** Component supports drag-and-drop interactions -- reordering items, moving between containers, file drop zones.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "drag" | Requires drop context |
| "drop" | Requires drag context |
| "drag-drop" | Sufficient alone (unambiguous UI) |
| "reorder" | Sufficient alone (unambiguous UI) |
| "drag to" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "drag-and-drop to reorder tasks" -> `has_drag_drop`
- "reorder kanban cards by dragging" -> `has_drag_drop`
- "drag files to the upload zone" -> `has_drag_drop`

DO NOT INJECT (EC-001 -- no UI context):
- "drop the database table" -> SQL DROP, not UI drag-drop
- "drag the performance metrics down" -> figurative, not UI interaction

**Ambiguous cases (requires >=2 signals):**
- "drag" alone -> ambiguous (needs drop context)
- "drag items and drop them in the target zone" -> sufficient (both drag and drop present)

**Gherkin template:**

```gherkin
Scenario: Drag item to new position
  Given a list of draggable items
  When the user drags item 1 below item 3
  Then the item is placed in the new position
  And the list order updates

Scenario: Drop target highlights on drag over
  Given the user is dragging an item
  When the item is dragged over a valid drop target
  Then the drop target is visually highlighted
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Drag start | `drag-start` | Drag operation initiates on mouse/touch hold |
| Drag over | `drag-over` | Drop target highlights during drag hover |
| Drop complete | `drop-complete` | Item placed at new position on drop |
| Drag constraints | `drag-constraints` | Drag respects axis and boundary constraints |

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| idle | `.draggable` | dragdrop-idle.png |
| dragging | `.draggable.is-dragging` | dragdrop-dragging.png |
| drop-target | `.drop-zone.active` | dragdrop-target.png |

---

### has_dirty_state

**Description:** Component detects unsaved changes and warns the user before navigating away -- dirty form detection, beforeunload prompts, save indicators.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "unsaved changes" | Sufficient alone (unambiguous UI) |
| "dirty state" | Sufficient alone (unambiguous UI) |
| "before unload" | Sufficient alone (unambiguous UI) |
| "discard changes" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "warn user about unsaved changes on navigation" -> `has_dirty_state`
- "dirty state indicator in the form header" -> `has_dirty_state`
- "discard changes confirmation dialog" -> `has_dirty_state` + `has_confirmation`

DO NOT INJECT (EC-001 -- no UI context):
- "dirty read in the database transaction" -> database concept, not UI
- "discard stale cache entries" -> cache management, not UI

**Ambiguous cases (requires >=2 signals):**
- All signals for this trait are sufficient alone (no ambiguous cases).

**Gherkin template:**

```gherkin
Scenario: Dirty indicator appears after edit
  Given a form in its clean state
  When the user modifies a field
  Then a "unsaved changes" indicator appears
  And the save button becomes enabled

Scenario: Warning shows on navigation away
  Given the form has unsaved changes
  When the user attempts to navigate away
  Then a warning dialog appears
  And the user can choose to stay or discard
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Dirty detection | `dirty-detection` | Changes detected and indicator shown |
| Unsaved warning | `unsaved-warning` | Navigation blocked with warning when dirty |
| Auto save | `auto-save` | Changes auto-saved periodically |

---

### is_optimistic

**Description:** Component updates the UI immediately before receiving server confirmation -- optimistic updates with rollback on failure.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "optimistic update" | Sufficient alone (unambiguous UI) |
| "instant feedback" | Requires server-sync context |
| "optimistic" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "optimistic update on like button click" -> `is_optimistic`
- "instant feedback with server sync" -> `is_optimistic` (server-sync context present)
- "optimistic UI for comment posting" -> `is_optimistic`

DO NOT INJECT (EC-001 -- no UI context):
- "optimistic concurrency control in the database" -> database concept, not UI
- "instant deployment with zero downtime" -> infrastructure, not UI

**Ambiguous cases (requires >=2 signals):**
- "instant feedback" alone -> ambiguous (could be validation feedback)
- "instant feedback with background server sync" -> sufficient (server-sync context present)

**Gherkin template:**

```gherkin
Scenario: UI updates immediately on action
  Given the user clicks the like button
  Then the like count increments immediately
  And a background request is sent to the server

Scenario: Rollback on server error
  Given an optimistic update was applied
  When the server returns an error
  Then the UI reverts to the previous state
  And an error message is displayed
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Optimistic update | `optimistic-update` | UI updates before server response |
| Rollback on error | `rollback-on-error` | UI reverts on server failure |
| Server sync | `server-sync` | Background sync confirms or rejects update |

---

### is_keyboard_navigable

**Description:** Component supports full keyboard navigation -- tab order, keyboard shortcuts, focus management, skip links for accessibility.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "keyboard navigation" | Sufficient alone (unambiguous UI) |
| "keyboard shortcuts" | Sufficient alone (unambiguous UI) |
| "tab order" | Sufficient alone (unambiguous UI) |
| "accessibility" | Requires keyboard context |
| "aria" | Requires navigation context |

**Detection examples:**

INJECT (positive examples):
- "full keyboard navigation with tab order" -> `is_keyboard_navigable`
- "keyboard shortcuts for common actions" -> `is_keyboard_navigable`
- "accessible dialog with keyboard focus management" -> `is_keyboard_navigable` (keyboard context present)

DO NOT INJECT (EC-001 -- no UI context):
- "accessibility audit report for the documentation" -> report, not UI behavior
- "aria labels in the HTML template" -> static markup, not navigation behavior

**Ambiguous cases (requires >=2 signals):**
- "accessibility" alone -> ambiguous (could be screen reader, not keyboard)
- "accessibility with keyboard navigation support" -> sufficient (keyboard context present)

**Gherkin template:**

```gherkin
Scenario: Tab key moves focus through interactive elements
  Given a page with multiple interactive elements
  When the user presses Tab
  Then focus moves to the next interactive element
  And the focus indicator is visible

Scenario: Enter activates focused element
  Given an interactive element has focus
  When the user presses Enter
  Then the element's action is triggered
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Keyboard focus | `keyboard-focus` | Tab moves focus through interactive elements |
| Shortcut trigger | `shortcut-trigger` | Keyboard shortcuts trigger correct actions |
| Skip links | `skip-links` | Skip navigation links work correctly |

---

### has_date_picker

**Description:** Component provides a date or time selection widget -- calendar pickers, date range selectors, time pickers.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "date picker" | Sufficient alone (unambiguous UI) |
| "calendar" | Requires date context |
| "date range" | Sufficient alone (unambiguous UI) |
| "time picker" | Sufficient alone (unambiguous UI) |

**Detection examples:**

INJECT (positive examples):
- "date picker for appointment booking" -> `has_date_picker`
- "calendar widget for selecting travel dates" -> `has_date_picker` (date context present)
- "date range selector for analytics" -> `has_date_picker`

DO NOT INJECT (EC-001 -- no UI context):
- "calendar sync with Google Calendar API" -> API integration, not UI widget
- "schedule a cron job for midnight" -> scheduling, not UI date picker

**Ambiguous cases (requires >=2 signals):**
- "calendar" alone -> ambiguous (could be calendar view, not picker)
- "calendar popup for date selection" -> sufficient (date context present)

**Gherkin template:**

```gherkin
Scenario: Calendar opens on input click
  Given a date input field
  When the user clicks the input
  Then the calendar widget opens
  And the current month is displayed

Scenario: Date selection closes picker
  Given the calendar is open
  When the user selects a date
  Then the selected date appears in the input
  And the calendar closes
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Date selection | `date-selection` | User can select a date from the calendar |
| Date validation | `date-validation` | Invalid dates are rejected with error |
| Date range | `date-range` | Start and end dates can be selected |

**Visual states:**

| State ID | CSS/Attributes | Screenshot |
|----------|----------------|------------|
| closed | `.datepicker[aria-expanded="false"]` | datepicker-closed.png |
| open | `.datepicker[aria-expanded="true"]` | datepicker-open.png |
| selected | `.date.selected` | datepicker-selected.png |

---

### has_rich_text

**Description:** Component provides a WYSIWYG or rich text editing experience -- text formatting, undo/redo, content paste handling.

**Detection signals:**

| Signal | Context requirement |
|--------|-------------------|
| "rich text" | Sufficient alone (unambiguous UI) |
| "WYSIWYG" | Sufficient alone (unambiguous UI) |
| "text editor" | Requires formatting context |
| "formatting" | Requires editor context |

**Detection examples:**

INJECT (positive examples):
- "rich text editor for blog posts" -> `has_rich_text`
- "WYSIWYG editor with toolbar" -> `has_rich_text`
- "text editor with bold/italic formatting" -> `has_rich_text` (formatting context present)

DO NOT INJECT (EC-001 -- no UI context):
- "text editor plugin for VS Code" -> IDE plugin, not UI component
- "formatting rules for log output" -> log formatting, not UI editor

**Ambiguous cases (requires >=2 signals):**
- "text editor" alone -> ambiguous (could be plain text editor)
- "text editor with rich formatting toolbar" -> sufficient (formatting context present)

**Gherkin template:**

```gherkin
Scenario: Bold formatting applied to selected text
  Given text is selected in the editor
  When the user clicks the Bold button
  Then the selected text is displayed in bold
  And the Bold button shows active state

Scenario: Undo/redo history works
  Given the user has applied formatting
  When the user clicks Undo
  Then the last formatting action is reversed
  When the user clicks Redo
  Then the formatting is re-applied
```

**Test patterns:**

| Pattern name | Pattern keyword | Description |
|-------------|----------------|-------------|
| Formatting apply | `formatting-apply` | Text formatting applied via toolbar |
| Undo redo | `undo-redo` | Undo/redo history functions correctly |
| Content paste | `content-paste` | Pasted content is sanitized and formatted |

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

<!-- @spec FR-008: 3 new transversal patterns — .specs/features/005.2-taxonomy-complete-expansion/spec.md#fr-008 -->

### filterable-sortable-table

**Constituent traits:** `is_sortable` + `is_filterable` + `has_selection`

**Disambiguation:** Apply when a table has both sort and filter capabilities. Do not apply if only one of sort/filter is present.

**Combined Gherkin template:**

```gherkin
Scenario: Table supports sort + filter + selection
  Given a table with 100 rows
  When the user filters by "status: active"
  Then only matching rows are displayed
  When the user sorts by "name" column
  Then rows are sorted alphabetically
  When the user selects rows 1-5
  Then 5 rows are selected
  And bulk actions are enabled
```

### notification-with-confirmation

**Constituent traits:** `shows_notification` + `has_confirmation`

**Disambiguation:** Apply when a destructive action shows a confirmation dialog and then displays a notification on completion. Do not apply if notification and confirmation are independent.

**Combined Gherkin template:**

```gherkin
Scenario: Destructive action shows confirmation then notification
  Given the user clicks "Delete account"
  Then a confirmation dialog appears
  When the user confirms deletion
  Then the account is deleted
  And a success notification is displayed
```

### drag-drop-list

**Constituent traits:** `has_drag_drop` + `has_dirty_state`

**Disambiguation:** Apply when a drag-drop reorder operation marks the list as having unsaved changes. Do not apply if drag-drop saves immediately (auto-save).

**Combined Gherkin template:**

```gherkin
Scenario: Drag to reorder marks list as dirty
  Given a todo list with 5 items
  When the user drags item 1 below item 3
  Then the list order updates
  And the "unsaved changes" indicator appears
  When the user saves changes
  Then the dirty state clears
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

### v2.0.0 (2026-04-17)
- Added 17 new traits across 5 categories: Navigation & Layout (4), Data Display (3), User Feedback (4), Advanced Interactions (4), Specialized Components (2)
- Added 3 new transversal patterns: filterable-sortable-table, notification-with-confirmation, drag-drop-list
- Total: 22 traits, 6 transversal patterns
- Visual states defined for: is_navigable, is_sortable, shows_notification, has_drag_drop, has_date_picker
- Feature: 005.2-taxonomy-complete-expansion

### v1.1.0 (2026-04-17)
- Added visual states tables for all 5 traits (is_submittable, async_action, has_overlay, dismissible_layer, has_validation)
- Feature: 009-visual-state-baselines

### v1.0.0 (2026-04-14)
- Initial taxonomy: 5 traits (is_submittable, async_action, has_overlay, dismissible_layer, has_validation)
- 3 transversal patterns (form-in-modal, inline-edit, async-search-select)
- Crash test: 84.6% coverage on 13 real-world components
- Deduplication rules (EC-002, EC-004)
- Asymmetric error handling (EC-005)

---

*Generated by livespec — 2026-04-17*

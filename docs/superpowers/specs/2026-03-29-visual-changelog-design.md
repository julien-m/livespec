# Design Spec: Visual Changelog — Screen History by Spec

> **Date:** 2026-03-29
> **Status:** Draft
> **Scope:** Design changelog format, PNG versioning per spec, validation UX, command updates (specify, spec-system), new template
> **Depends on:** Design Integration (2026-03-23)

---

## 1. Problem Statement

The current design integration stores PNGs as latest-only (`screens/<name>.png`), overwriting previous versions on each spec. The design changelog is a flat chronological log grouped by date/feature — not navigable by screen.

This means:

- **No visual before/after:** When a spec modifies an existing screen, the previous version is lost (only recoverable via `git show`)
- **No screen-centric history:** To see the evolution of "dashboard", you must scan every changelog entry looking for that screen name
- **No clickable navigation:** The changelog has no links to the actual PNG files
- **No comparison during validation:** When `/spec.specify` asks the user to validate a mockup, it doesn't show the previous version for comparison

Since each spec generates mockups and the user validates before continuing, the history builds naturally — we just need to stop overwriting and provide a navigable index.

---

## 2. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PNG storage | `screens/<NNN-feature-name>/<name>.png` (one folder per feature) | Natural grouping, no ambiguity, same naming as feature dirs |
| Latest link | Keep `screens/<name>.png` as a copy of the latest version | plan.md, implement.md, check.md reference `screens/<name>.png` — zero breaking change |
| Changelog format | Screen-centric tables with clickable links | Primary use case is "see evolution of one screen" |
| Changelog location | `.specs/design/changelog.md` (same as today) | No change in location, only format |
| Validation UX | Show link to previous version during mockup validation | Enables before/after comparison at the moment it matters |
| Notes column | One-liner per entry describing what changed | Avoids opening the spec to understand why a screen evolved |
| Template | New `design-changelog-template.md` | Format is specific enough to warrant its own template |

---

## 3. Architecture

### 3.1 PNG Storage — Versioned by Feature

**Current** (latest-only, overwritten):
```
.specs/design/screens/
├── dashboard.png
├── settings.png
└── login.png
```

**New** (versioned per feature + latest copy):
```
.specs/design/screens/
├── dashboard.png              ← latest copy (for plan/implement/check references)
├── settings.png               ← latest copy
├── login.png                  ← latest copy
│
├── 001-user-auth/
│   ├── login.png              ← version from spec 001
│   └── dashboard.png          ← version from spec 001
│
├── 003-notifications/
│   ├── dashboard.png          ← version from spec 003 (dashboard modified)
│   └── notification-panel.png ← new screen in spec 003
│
└── 007-settings-redesign/
    └── settings.png           ← version from spec 007
```

**Rules:**
- Feature subfolder uses the same `NNN-feature-name` convention as `.specs/features/`
- Each PNG in a feature subfolder is immutable — never overwritten
- `screens/<name>.png` (root level) is always a copy of the latest version of that screen across all features
- When a new spec generates/modifies a screen: save to `screens/<NNN-feature-name>/<name>.png` AND copy to `screens/<name>.png`
- Git tracks everything — both the immutable versions and the latest copies

### 3.2 Design Changelog — Screen-Centric Format

**Current format** (chronological, flat):
```markdown
### 2026-03-15 — Feature 001: User Auth

- **login.png** — new screen (login form with social auth)
- **dashboard.png** — modified (added user avatar)
```

**New format** (grouped by screen, with clickable links):

```markdown
# Design Changelog

> Screen-by-screen visual history. Each entry links to the spec and the PNG for direct comparison.

---

## dashboard

| Spec | Date | Mockup | Notes |
|------|------|--------|-------|
| [001-user-auth](../features/001-user-auth/spec.md) | 2026-02-15 | [📸](screens/001-user-auth/dashboard.png) | Initial layout with user avatar |
| [003-notifications](../features/003-notifications/spec.md) | 2026-03-10 | [📸](screens/003-notifications/dashboard.png) | Added notification widget top-right |
| [012-analytics](../features/012-analytics/spec.md) | 2026-03-28 | [📸](screens/012-analytics/dashboard.png) | Added stats grid below header |

**Latest:** [dashboard.png](screens/dashboard.png)

---

## login

| Spec | Date | Mockup | Notes |
|------|------|--------|-------|
| [001-user-auth](../features/001-user-auth/spec.md) | 2026-02-15 | [📸](screens/001-user-auth/login.png) | Login form with social auth buttons |

**Latest:** [login.png](screens/login.png)

---

## notification-panel

| Spec | Date | Mockup | Notes |
|------|------|--------|-------|
| [003-notifications](../features/003-notifications/spec.md) | 2026-03-10 | [📸](screens/003-notifications/notification-panel.png) | Slide-out panel with notification list |

**Latest:** [notification-panel.png](screens/notification-panel.png)
```

**Rules:**
- Screens are sorted alphabetically (h2 headings)
- Within each screen, entries are chronological (oldest first)
- The `📸` emoji is the clickable link to the versioned PNG
- The `Spec` column links to the feature's spec.md for context
- The `Notes` column is a one-liner describing what changed on this screen (not the full feature description)
- `**Latest:**` link after each table points to the root-level latest copy
- New screens get a single-row table on their first appearance

### 3.3 Validation UX — Before/After During Specify

When `/spec.specify` Step 5.6 generates mockups for a screen that already exists in the changelog, the validation gate shows the previous version link:

**Current validation gate:**
```
🎨 Mockups generated for [feature name]:
  • dashboard.png (modified — added stats grid)
  • analytics-panel.png (new)

Exported to .specs/design/screens/

→ Approve mockups to continue, or describe changes needed.
```

**New validation gate (for modified screens):**
```
🎨 Mockups generated for [feature name]:
  • dashboard.png (modified — added stats grid)
    ↳ Previous: 003-notifications (2026-03-10) — [📸](screens/003-notifications/dashboard.png)
  • analytics-panel.png (new)

Exported to .specs/design/screens/012-analytics/

→ Open the design tool to review and save the source file:
  open .specs/design/ui.<ext>

→ Approve mockups to continue, or describe changes needed.
```

**Logic:**
1. For each screen being generated, check if it already has entries in `changelog.md`
2. If yes → find the last entry (last row of that screen's table) and display it with a link
3. If no → mark as "(new)", no previous version shown
4. The user can click the 📸 link to open the previous PNG and compare side by side

### 3.4 Spec Screen References — Updated Paths

The `## Screens` section in `spec.md` now references the versioned path:

```markdown
## Screens

| Screen | Status | Reference |
|--------|--------|-----------|
| dashboard | Modified | [dashboard.png](../../design/screens/012-analytics/dashboard.png) |
| analytics-panel | New | [analytics-panel.png](../../design/screens/012-analytics/analytics-panel.png) |
```

**Note:** The reference points to the feature-specific version (immutable), not the latest copy. This ensures the spec always shows the mockup that was validated for THIS feature, even if later features modify the same screen.

**Path divergence by document (deliberate):**
- `spec.md` and `plan.md` → reference the **immutable** versioned path (`screens/<NNN-feature-name>/<name>.png`). These documents record the contract at the time of specification — they must not shift when a later feature updates the same screen.
- `implement.md` and `check.md` → reference the **latest** copy (`screens/<name>.png`). Implementation targets the current state of the screen, and fidelity checks compare against the current mockup.

This divergence is by design and should not be "fixed."

### 3.5 Backward Compatibility

- `screens/<name>.png` (latest copy) continues to exist → `plan.md`, `implement.md`, and `check.md` references work unchanged
- Old design integration spec rule "PNGs are overwritten" becomes "latest copy is overwritten, versioned copy is immutable"
- Existing projects without versioned folders: first `/spec.specify` run creates the feature subfolder. Previous PNGs remain at root level as the "latest" — no migration needed.

---

## 4. Command Updates

### 4.1 `/spec.specify` — Step 5.6 Changes

Replace sub-steps 5 through 8 within the current Step 5.6 (flat numbering preserved):

**Sub-step 5 — Export assets (replaces current sub-step 5):**
1. Create feature subfolder: `.specs/design/screens/<NNN-feature-name>/`
2. Export each screen PNG to `.specs/design/screens/<NNN-feature-name>/<screen-name>.png`
3. Copy each PNG to `.specs/design/screens/<screen-name>.png` (latest)
4. Export PDF to `.specs/design/ui.pdf`

**Sub-step 6 — Validation gate (replaces current sub-step 6):**
1. For each screen, check `changelog.md` for previous entries
2. Display validation message with previous version links (Section 3.3)

**Sub-step 7 — Screen references (replaces current sub-step 7):**
1. Add `## Screens` section with paths to feature-specific PNGs (Section 3.4)

**Sub-step 8 — Update design changelog (replaces current sub-step 8):**
1. Read current `changelog.md`
2. For each screen generated:
   a. If screen already has a section (h2) → append a new row to its table
   b. If screen is new → create a new h2 section with a single-row table, inserted in alphabetical order among existing screen sections
3. Update the `**Latest:**` link
4. Date = the date when `/spec.specify` runs. On re-specification, the date is updated to the current date.
5. Write the updated `changelog.md`

### 4.2 `/spec.specify` — Re-modification Workflow Update

When re-specifying an existing feature:
- Overwrite PNGs in the feature's own subfolder (`screens/<NNN-feature-name>/`)
- Update the latest copy at root level
- Update the existing row in the changelog (same spec, same screen → update, not append)

### 4.3 `spec-system.md` — Layout Tree Update

Update the design directory structure:

```
├── design/
│   ├── ui.<ext>            ← Design source file (tool-specific)
│   ├── ui.pdf              ← Full PDF export
│   ├── screens/            ← Per-screen PNG exports
│   │   ├── *.png           ← Latest version of each screen
│   │   └── NNN-feature-name/  ← Versioned PNGs per feature
│   │       └── *.png
│   └── changelog.md        ← Screen-centric visual history
```

### 4.4 Design Integration Spec — Updates

Update the following in `2026-03-23-design-integration-design.md`:

- **Section 3.3** — change "Latest only" to "Versioned per feature + latest copy"
- **Section 3.5.3 step 5** — update export paths
- **Section 3.5.3 step 7** — update screen references to feature-specific paths
- **Section 3.5.3 step 8** — update changelog format
- **Section 3.5.4** — update re-modification to use feature subfolder
- **Decision table row "Versioning strategy"** — update from "Latest only" to "Per-feature + latest copy"
- **Rule 4 in Section 6.3** — update "overwrite the PNG" to "save versioned + update latest copy"

---

## 5. New Template

### `system/templates/design-changelog-template.md`

```markdown
# Design Changelog

> Screen-by-screen visual history. Each entry links to the spec and the PNG for direct comparison.
> This file is auto-maintained by `/spec.specify`. Manual edits are allowed but may be overwritten.

---

<!-- Add a ## section per screen, alphabetically sorted. Each section has a table + Latest link. -->
<!-- Example:

## screen-name

| Spec | Date | Mockup | Notes |
|------|------|--------|-------|
| [NNN-feature-name](../features/NNN-feature-name/spec.md) | YYYY-MM-DD | [📸](screens/NNN-feature-name/screen-name.png) | Description of what changed |

**Latest:** [screen-name.png](screens/screen-name.png)

-->
```

---

## 6. Edge Cases

- **First spec with UI in a project:** No changelog exists yet → create it from template, add the first screen sections
- **Feature modifies a screen created by a previous feature:** Append row to existing screen table, update latest copy
- **Two features modify the same screen on the same day:** Both get their own rows — the date alone doesn't disambiguate, the spec link does
- **Feature creates a screen then later another feature deletes it:** Mark the screen section with `~~Deprecated~~` and note in the last row. Don't delete the section — history is preserved.
- **Re-specification of same feature:** Update the existing row (same spec + screen), don't create a duplicate row
- **Changelog doesn't exist yet (pre-Visual-Changelog projects):** First `/spec.specify` creates it. Existing root-level PNGs are treated as "unversioned legacy" — no retroactive migration.
- **Feature renumbered or renamed after initial spec:** Versioned folders and changelog entries are immutable — they keep the original `NNN-feature-name`. No retroactive renaming. Git history stays clean and links remain valid.

---

## 7. Files to Create/Modify

### Create

| File | Description |
|------|-------------|
| `system/templates/design-changelog-template.md` | Template for the screen-centric design changelog |

### Modify

| File | Change |
|------|--------|
| `commands/specify.md` | Update Step 5.6: versioned export paths, new validation UX with previous version, screen-centric changelog update, feature-specific screen references in spec.md |
| `system/spec-system.md` | Update design directory layout tree to show versioned structure |
| `docs/superpowers/specs/2026-03-23-design-integration-design.md` | Update versioning strategy, export paths, changelog format, re-modification workflow |

---

*Design Spec — Visual Changelog v1.0*

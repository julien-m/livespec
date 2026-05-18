# Implementation Plan: Visual Changelog — Screen History by Spec

> **Date:** 2026-03-29
> **Design Spec:** [2026-03-29-visual-changelog-design.md](../specs/2026-03-29-visual-changelog-design.md)
> **Depends on:** Design Integration (2026-03-23)

---

## Summary

Add PNG versioning per feature, replace the flat design changelog with screen-centric tables with clickable links, and show the previous version during mockup validation.

---

## Tasks

### T1 — Create `design-changelog-template.md`

**File:** `system/templates/design-changelog-template.md`

Create the new template with the screen-centric format as defined in Design Spec Section 5.

**Acceptance:** Template file exists with the header, description, and commented example.

---

### T2 — Update `spec-system.md` layout tree

**File:** `system/spec-system.md`

Update the `design/` section in the Project Layout tree (around line 73-78):

**From:**
```
├── design/
│   ├── ui.<ext>            ← Design source file (tool-specific)
│   ├── ui.pdf              ← Full PDF export
│   ├── screens/            ← Per-screen PNG exports
│   │   └── *.png
│   └── changelog.md        ← Design change history
```

**To:**
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

Also update the "When working with DESIGN mockups" rules section — change rule 4 from "overwrite the PNG" to "save versioned copy + update latest copy".

**Acceptance:** Layout tree shows versioned structure. Rules reflect new behavior.

---

### T3 — Update `commands/spec-specify.md` Step 5.6

**File:** `commands/spec-specify.md`

Replace sub-steps 5 through 8 within Step 5.6 (lines ~269-308):

**Sub-step 5 (Export):** Change export path from `screens/<name>.png` to `screens/<NNN-feature-name>/<name>.png` + copy to `screens/<name>.png` (latest).

**Sub-step 6 (Validation):** Add previous version lookup from changelog. For modified screens, show the link to the last version with `↳ Previous: ...` line.

**Sub-step 7 (Screen refs):** Change spec.md references to point to versioned path `screens/<NNN-feature-name>/<name>.png`.

**Sub-step 8 (Changelog):** Replace chronological entry format with screen-centric table update:
- Parse existing changelog for screen h2 sections
- Append row to existing screen table or create new section (alphabetically ordered)
- Update `**Latest:**` link
- Date = run date; re-spec updates date

**Re-modification section** (line ~308): Update to use feature subfolder. On re-spec of same feature, overwrite PNG in own subfolder + update existing changelog row (not append).

**Acceptance:** Step 5.6 reflects all 4 sub-step changes + re-modification workflow.

---

### T4 — Update design integration spec

**File:** `docs/superpowers/specs/2026-03-23-design-integration-design.md`

Update to align with the visual changelog:

1. **Decision table (Section 2):** "Versioning strategy" row — change "Latest only, git handles history" to "Per-feature versioned + latest copy at root"
2. **Section 3.3:** Update directory structure to show versioned subfolders + latest copies
3. **Rules in Section 3.3:** Change "always overwritten (latest version only)" to "immutable per-feature + latest copy overwritten"
4. **Section 3.5.3 step 5:** Update export paths
5. **Section 3.5.3 step 7:** Update screen reference paths in spec.md
6. **Section 3.5.3 step 8:** Update changelog entry format to screen-centric
7. **Section 3.5.4:** Update re-modification to save in feature subfolder
8. **Section 6.3 rule 4:** Change "overwrite the PNG" to "save versioned + update latest copy"

**Acceptance:** Parent spec is consistent with visual changelog spec. No contradictions.

---

## Task Dependencies

```
T1 (template)     ─── independent
T2 (spec-system)  ─── independent
T3 (specify.md)   ─── independent
T4 (design spec)  ─── independent
```

All tasks are independent and can be parallelized.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Changelog format change breaks existing projects | Low | No existing projects use the design changelog yet (design integration is documented but `.specs/` not created) |
| Step numbering confusion in specify.md | Low | Using same flat sub-step numbering as parent |

---

*Implementation Plan — Visual Changelog v1.0*

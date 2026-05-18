# Design: Playwright gitignore — spec.init + migration v6

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** Small — `commands/spec-init.md` and `migrations/6/migrate.md`

---

## Problem

`spec.init` (commands/spec-init.md step 3.12) only adds 3 gitignore patterns (LiveSpec symlink artifacts). It does not add Playwright output directories:
- `test-results/` — Playwright test artifacts (screenshots, videos, traces)
- `playwright-report/` — Playwright HTML reporter output

Migration v3 added `test-results/` for existing projects. Migration v6 will add `playwright-report/` for existing projects. But new projects created via `spec.init` have never had either pattern — they remain exposed until a migration runs.

---

## Solution

### 1. commands/spec-init.md — Step 3.12

Add `test-results/` and `playwright-report/` to the gitignore update list in step 3.12. These are added unconditionally (not gated on Playwright detection) for two reasons:
- Consistent with how other LiveSpec patterns are added (no detection gate)
- Harmless if Playwright is never used (empty gitignore entry does nothing)

**Before:**
```
6. **Update .gitignore:** Add the following patterns (if not already present):
   - `.claude/commands/spec.*.md`
   - `.claude/agents/livespec-*.md`
   - `.specs/.livespec-path`
```

**After:**
```
6. **Update .gitignore:** Add the following patterns (if not already present):
   - `.claude/commands/spec.*.md`
   - `.claude/agents/livespec-*.md`
   - `.specs/.livespec-path`
   - `test-results/`
   - `playwright-report/`
```

Also update the Definition of Done checklist in init.md to reflect the new patterns.
Remove the duplicate `.gitignore` instruction from step 3.13 so the behavior is defined in one place.

### 2. migrations/6/migrate.md — New file

Adds `playwright-report/` for projects that already ran migration v3 (which added `test-results/`).

```markdown
---
version: 6
description: "Add playwright-report/ to .gitignore"
date: 2026-04-14
---

# Migration v6: Playwright Report Gitignore

Adds playwright-report/ to .gitignore. This is Playwright's HTML reporter
output directory, distinct from test-results/ (test artifacts) which was
added in migration v3.

## Actions

GITIGNORE playwright-report/
SET_VERSION 6
```

---

## Files Modified

| File | Change |
|------|--------|
| `commands/spec-init.md` | Add `test-results/` and `playwright-report/` to step 3.12 gitignore list, remove the duplicate step 3.13 instruction, and collapse the DoD into one unconditional checklist item |
| `migrations/6/migrate.md` | New file — GITIGNORE playwright-report/ + SET_VERSION 6 |

---

## Edge Cases

- **Project already has these entries in .gitignore:** GITIGNORE instruction is idempotent (checks before appending). No duplicates.
- **Project never uses Playwright:** Harmless — empty gitignore entries have no effect.
- **Project on migration v3 or v4:** Migration v6 will add the missing playwright-report/ entry.
- **Project on v5:** Same — migration v6 adds playwright-report/.

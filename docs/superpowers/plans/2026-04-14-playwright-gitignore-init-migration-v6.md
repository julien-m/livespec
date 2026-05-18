# Plan: Playwright gitignore — spec.init + migration v6

**Date:** 2026-04-14  
**Design:** `docs/superpowers/specs/2026-04-14-playwright-gitignore-init-migration-v6-design.md`

---

## Task 1 — Update commands/spec-init.md (step 3.12)

**File:** `commands/spec-init.md`

Locate the step 3.12 block (~line 766):
```
6. **Update .gitignore:** Add the following patterns (if not already present):
   - `.claude/commands/spec.*.md`
   - `.claude/agents/livespec-*.md`
   - `.specs/.livespec-path`
```

Replace it with:
```
6. **Update .gitignore:** Add the following patterns (if not already present):
   - `.claude/commands/spec.*.md`
   - `.claude/agents/livespec-*.md`
   - `.specs/.livespec-path`
   - `test-results/`
   - `playwright-report/`
```

- [ ] Read `commands/spec-init.md` before editing
- [ ] Apply the edit
- [ ] Re-read to confirm

Then remove this duplicate instruction from step 3.13:
```
- **Add `.gitignore` entries** (if not already present): `test-results/` and `playwright-report/`
```

- [ ] Confirm `.gitignore` patterns are documented only once, in step 3.12

---

## Task 2 — Update the DoD checklist in init.md

In the Definition of Done section (~line 985), locate these lines:
```
- [ ] `.gitignore` contains `.claude/commands/spec.*.md`, `.claude/agents/livespec-*.md`, `.specs/.livespec-path`
- [ ] If `@playwright/test` detected: `.gitignore` contains `test-results/` and `playwright-report/`
```

Replace them with:
```
- [ ] `.gitignore` contains `.claude/commands/spec.*.md`, `.claude/agents/livespec-*.md`, `.specs/.livespec-path`, `test-results/`, `playwright-report/`
```

- [ ] Apply the edit in the same `init.md` pass
- [ ] Re-read to confirm the requirement is unconditional

---

## Task 3 — Create migrations/6/migrate.md

**File:** `migrations/6/migrate.md` (new)

Create the directory and file:

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

- [ ] Create `migrations/6/`
- [ ] Write `migrations/6/migrate.md`
- [ ] Re-read to confirm

---

## Execution Order

Tasks 1 and 2 run sequentially in the same file. Task 3 can proceed after the initial read.

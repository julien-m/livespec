# Design: Roadmap Lifecycle — Re-evaluation, Emerging Dependencies & Manual Management

> **Date:** 2026-03-26
> **Status:** Draft
> **Scope:** 2 commands modified (refine, specify) + spec-system.md update
> **Depends on:** [spec-roadmap-design](2026-03-26-spec-roadmap-design.md)

---

## Problem

The roadmap (`.specs/roadmap.md`) is generated at init and updated during specify (split detection + checkbox sync). But it has three lifecycle gaps:

1. **Staleness after project changes:** When `/spec.refine project` modifies roles, vision, or constraints, roadmap items may become obsolete or new ones may be needed. No re-evaluation happens.

2. **Emerging dependencies:** When `/spec.specify` generates a spec, it may reference entities, services, or capabilities that don't exist anywhere — not in features, not in the roadmap. These implicit dependencies are lost.

3. **No manual management:** There's no way for the user to directly remove, reorganize, or modify roadmap items. The roadmap is write-only from the user's perspective.

---

## Design

### 1. Refine Project — Step 5.5: Roadmap Re-evaluation

New step inserted between Step 5 (Apply and Record) and the changelog update, in the **Flow: Project** section of `refine.md`.

**Trigger:** Runs automatically after any project-level change is applied (project.md, constitution.md, or testing/strategy.md). Skipped if `.specs/roadmap.md` does not exist.

**Logic:**

1. Read the updated `project.md` (post-change)
2. Re-run the inference matrix from `spec.init` Step 3.9 on the updated profile:

| Signal from project profile | Expected domain |
|---|---|
| Any project with users | Authentication |
| Multiple roles with different access | Role management / RBAC |
| Role has "post", "create", "manage" actions | CRUD for that entity |
| Real-time messaging mentioned | Messaging system |
| Real-time notifications mentioned | Notification system |
| "Search", "browse", "discover" in vision | Search & discovery |
| "Pay", "invoice", "billing", "monetize" | Payments / billing |
| Admin role exists | Admin dashboard |
| "Mobile" or "responsive" mentioned | Mobile-optimized views |
| "Analytics", "reports", "metrics" | Reporting & analytics |
| "Settings", "preferences", "profile" | User settings / profiles |

3. Compare inferred items against existing roadmap items (all tiers + Deferred)
4. Compute the delta:
   - **New items:** inferred but not in roadmap → propose adding
   - **Stale items:** in roadmap (unchecked) but no longer inferred from updated profile → mark `[STALE?]` and propose removal
   - **Modified items:** scope or dependencies changed due to profile change → propose update
   - **Checked items** (already specified) are never marked stale — they exist as specs regardless of profile changes

5. Present the delta as a diff:

```
📋 Roadmap re-evaluation after project change:

  + **Reviewer dashboard** — new role "Reviewer" needs management tools · Scope: M · Tier: Post-MVP
  + **Comment system** — Reviewers can leave comments on deliverables · Scope: M · Tier: MVP
  ~ **Admin dashboard** — scope updated: now includes Reviewer moderation · Scope: M → L
  ? **Mobile-optimized views** [STALE?] — "mobile" no longer mentioned in vision

  Apply these changes to roadmap.md? (y/n/modify)
```

Legend: `+` = add, `~` = modify, `?` = stale (propose removal)

6. **If confirmed:** apply changes to `roadmap.md` — add new items, update modified items, remove stale items
7. **If "modify":** let user adjust individual items before applying
8. **If declined:** no changes to roadmap

**Edge cases:**
- No roadmap.md → skip silently
- No delta detected → display "Roadmap is up to date" and skip
- `--auto` flag → apply delta without confirmation
- `--dry-run` flag → show delta but don't apply

---

### 2. Refine Project — Roadmap as 4th Target

Add `roadmap.md` as a directly refinable target in the Project flow.

**Step 2 — Present Summary** (updated menu):

```
What would you like to refine?
1. Users, roles, or constraints (project.md)
2. Architecture principles (constitution.md)
3. Testing strategy (testing/strategy.md)
4. Roadmap (roadmap.md)
5. Describe your change freely
```

**When option 4 is selected — Roadmap Refinement Flow:**

1. Read `.specs/roadmap.md`
2. Present the current roadmap state:

```
## Current Roadmap

### MVP (3 items — 1 ✅, 2 ⬜)
  ✅ User auth → 001-user-auth
  ⬜ Job listings · Scope: M · Deps: auth
  ⬜ Designer profiles · Scope: M · Deps: auth

### Post-MVP (2 items — 0 ✅, 2 ⬜)
  ⬜ Notifications · Scope: M · Deps: messaging
  ⬜ Payments · Scope: L · Deps: job-listings

### Future (1 item)
  ⬜ Search & discovery · Scope: M

### Deferred (1 item)
  Audit trail (from "auth + audit") · Scope: S

What would you like to do?
1. Remove items
2. Move items between tiers
3. Add a new item
4. Modify an item (scope, deps, description)
5. Describe your change
```

3. Execute the selected action with before/after diff and confirmation
4. Apply changes + update `Last updated` date
5. Changelog entry: `[Project] Roadmap refined: [description]`

**Numbering note:** Roadmap items don't have IDs — they're identified by their bold name. No renumbering concern (unlike AC/FR).

---

### 3. Specify — Step 5.5: Emerging Dependencies & Absorption Detection

New step inserted in `specify.md` between Step 5 (Generate spec.md) and the existing Step 5.5 (Generate Mockups). The existing Step 5.5 becomes Step 5.6.

**Logic:**

1. Read the just-generated `spec.md`
2. Extract all referenced entities, services, and capabilities from:
   - Key Entities section
   - Functional Requirements (FR references to external systems)
   - User stories (mentions of features the user expects to exist)
   - Infrastructure Requirements (if present)
3. Read `.specs/features/*/spec.md` headers — build list of existing feature names and key entities
4. Read `.specs/roadmap.md` (if exists) — build list of roadmap items (all tiers + Deferred)

**Detection A — Emerging dependencies:**

5. For each referenced entity/capability NOT found in existing features OR roadmap:
   - It's an **emerging dependency** — something this spec assumes will exist but nobody planned

6. If emerging dependencies found, present:

```
📋 Emerging dependencies detected in this spec:

| Dependency | Found in | Suggested tier | Source in spec |
|-----------|----------|---------------|----------------|
| Push notifications | — (nowhere) | Post-MVP | FR-003: message alerts |
| Organization entity | — (nowhere) | MVP | Key Entities: multi-tenant |

→ Add to roadmap? (y/n)
```

7. If confirmed: add items to appropriate tier in `roadmap.md`

**Detection B — Absorption:**

8. For each existing unchecked roadmap item, check if the current spec **covers it** — i.e., the spec's user stories, entities, or FR substantially overlap with the roadmap item's description
9. Match criteria: the spec's key entities or FR descriptions contain the roadmap item's bold name or primary domain keyword (case-insensitive)

10. If absorption detected, present:

```
📋 This spec appears to cover existing roadmap items:

| Roadmap item | Tier | Overlap |
|-------------|------|---------|
| Push notifications | Post-MVP | Covered by FR-003 + Story 3 |

→ Check these items as covered? (y/n)
```

11. If confirmed: check the item in roadmap (`- [ ]` → `- [x]`) and link to this spec

**Edge cases:**
- No roadmap.md → skip both detections silently
- No emerging deps and no absorption → skip silently (no output)
- `--auto` flag → add emerging deps and check absorbed items without confirmation

---

### 4. Specify — Step 5.5 renumbering

The current Step 5.5 (Generate Mockups) becomes **Step 5.6**. All references to "Step 5.5" in the file must be updated to "Step 5.6". This affects:
- The step header itself
- Any cross-references within the file (Step 6 Quality Validation references to mockups)
- The Definition of Done checklist items referencing Step 5.5

---

### 5. spec-system.md Updates

Add to the README.md update rules section:

```
- `/spec.refine project` re-evaluates roadmap after project profile changes + supports direct roadmap refinement
- `/spec.specify` detects emerging dependencies and roadmap item absorption
```

---

### 6. Definition of Done Updates

**`/spec.refine` (project flow):**
- `[ ] If roadmap.md exists and project-level changes applied: roadmap re-evaluation executed`
- `[ ] If roadmap option selected: changes applied with before/after diff`

**`/spec.specify`:**
- `[ ] If roadmap.md exists: emerging dependencies detected and proposed (or none found)`
- `[ ] If roadmap.md exists: absorption detection run (or no overlap found)`

---

### 7. Edge Cases

| Case | Behavior |
|------|----------|
| No roadmap.md | All roadmap operations skip silently |
| Refine project with no delta | Display "Roadmap is up to date", no changes |
| Refine roadmap — remove checked item | Warn: "This item has a spec (NNN-name). Removing from roadmap does not delete the spec." Allow removal. |
| Refine roadmap — move checked item between tiers | Allow — preserves the check and link |
| Absorption of Deferred item | Remove from Deferred table, add as checked item in appropriate tier (same as Step 7.7 deferred match) |
| Specify with --auto | Auto-add emerging deps, auto-check absorbed items |
| Refine with --dry-run | Show delta/diff but don't apply |
| Multiple specs absorb same roadmap item | First spec to absorb checks it — subsequent specs see it as already checked |

---

### 8. Files Modified

| File | Change |
|------|--------|
| `commands/refine.md` | Add Step 5.5 (roadmap re-evaluation) to Project flow, add roadmap as 4th menu target with full refinement flow, update DoD |
| `commands/specify.md` | Add Step 5.5 (emerging deps + absorption), renumber existing Step 5.5 → 5.6, update DoD |
| `system/spec-system.md` | Add roadmap lifecycle rules to README update rules |

---

### 9. What This Does NOT Change

- No new commands created
- No changes to `/spec.init`, `/spec.plan`, `/spec.implement`, `/spec.check`, `/spec.propose`
- The inference matrix is not duplicated — refine.md references the same matrix defined in init.md Step 3.9
- Roadmap template format unchanged
- Existing Step 7.7 (roadmap sync) in specify.md unchanged

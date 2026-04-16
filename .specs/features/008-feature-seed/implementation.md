# Implementation — 008 Feature Seed

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|-------------|---------|-------------|--------|---------------|
| FR-001 | commands/specify.md | `@spec FR-001: Seed creation step after split` | ✅ Implemented | 2026-04-16 |
| FR-002 | commands/specify.md | `@spec FR-002: Seed detection and context injection` | ✅ Implemented | 2026-04-16 |
| FR-003 | commands/specify.md | `@spec FR-003: Seed absorption after spec generation` | ✅ Implemented | 2026-04-16 |
| FR-004 | commands/specify.md | `@spec FR-004: 4-field Markdown schema with placeholders` | ✅ Implemented | 2026-04-16 |
| FR-005 | .specs/spec-system.md | `@spec FR-005: Document seed artifacts in spec-system` | ✅ Implemented | 2026-04-16 |
| FR-006 | commands/specify.md | `@spec FR-006: Origin field structure` | ✅ Implemented | 2026-04-16 |
| FR-007 | commands/specify.md | `@spec FR-007: Seeded attribution in Input section` | ✅ Implemented | 2026-04-16 |

## Acceptance Criteria Mapping

| AC | Satisfied By | Status |
|----|-------------|--------|
| AC-001 | Step 1.5.5.1 creates seed.md alongside roadmap entry | ✅ Implemented |
| AC-002 | Step 1.5.5.1 template has 4 sections: Origin, Decisions, Constraints, Open Questions | ✅ Implemented |
| AC-003 | Step 1.5.5.1 Origin field includes parent number+name, split reason, date | ✅ Implemented |
| AC-004 | Step 1.7 loads seed.md and injects as Seed Context in LLM prompt | ✅ Implemented |
| AC-005 | Step 1.7 checks spec.md existence before seed loading; spec.md takes precedence | ✅ Implemented |
| AC-006 | Step 7.3 renames seed.md to seed.absorbed.md (content-preserving rename) | ✅ Implemented |
| AC-007 | Step 1.7 only checks for seed.md, never seed.absorbed.md; Step 7.3 skips if already absorbed | ✅ Implemented |
| AC-008 | Step 1.5.5.1 creates feature directory with next available NNN if it does not exist | ✅ Implemented |
| AC-009 | Step 1.5.5.1 only runs within the split loop; no split = no seed | ✅ Implemented |
| AC-010 | Step 1.5.5.1 specifies placeholder text "None yet -- to be determined at specify time" | ✅ Implemented |
| AC-011 | spec-system.md Feature Directory Structure lists seed.md and seed.absorbed.md | ✅ Implemented |

## Files Modified

| File | What Changed |
|------|-------------|
| `commands/specify.md` | Added Step 1.7 (Seed Detection), Step 1.5.5.1 (Seed Creation), Step 7.3 (Seed Absorption) |
| `.specs/spec-system.md` | Added seed.md and seed.absorbed.md to directory tree and documentation subsections |

## Files Created

| File | Purpose |
|------|---------|
| `.specs/features/008-feature-seed/implementation.md` | This file -- requirement mapping |
| `.specs/features/008-feature-seed/progress.md` | Step-by-step checkpoint tracker |

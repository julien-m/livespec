# Audit Fixes — Design Spec

> Fix all P0–P2 findings from the Copilot audit of 2026-03-24.

## Scope

9 targeted fixes across scripts, docs, and command files. No new features — alignment and coherence only.

## Changes

### P0 — Critical

1. **Align init.sh CLAUDE.md block** — list all 13 commands (currently 8)
2. **Clean spec-system.md** — remove phantom `.specs/commands/` tree and `link.md`, fix command discovery section

### P1 — Important

3. **Standardize Playwright** — replace `playwright-cli` references in `discovery.md` with `npx playwright`
4. **Add `play-coverage` to hooks** — update valid command list in `system/hooks.md` and `commands/hooks.md`
5. **Preflight: add superpowers + agent teams checks** — add to Stack-to-Checks catalog in `commands/preflight.md`
6. **Preflight: add `creds` binary check** — add creds detection to catalog

### P2 — Nice-to-have

7. **Clarify tool-agnostic in README** — add Portability section distinguishing format vs automation
8. **Create `scripts/check-coherence.sh`** — validate commands count, broken refs, path consistency
9. **Delete `audit.md`** — remove the Copilot audit file (served its purpose)

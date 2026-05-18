---
name: spec-refresh-conventions
description: Migrated Claude command /spec-refresh-conventions
---

# /spec-refresh-conventions

---
description: "Manually initialize or refresh project conventions from the LiveSpec stack"
---

<!-- Anti-drift block injected via @import (Chantier 1, AUDIT.md). See system/anti-drift-block.md for the canonical 6-field step shape, ERROR/BLOCKED line formats, and timeout/retry policy. -->
<!-- @import system/anti-drift-block.md -->


# Command: /spec-refresh-conventions

> Manually trigger generation or regeneration of the project's conventions bundle (`.conventions/index.md` + `.conventions/manifest.yaml`) from the current LiveSpec stack.

---

## Overview

`/spec-refresh-conventions` runs the **Bootstrap Path** defined in `~/.claude/livespec/references/conventions-sync.md`, with verbose output. Use it when:

- `/spec-init` ran but conventions were not generated (e.g., the `after-init` hook was not triggered).
- The stack changed and you want to rebuild conventions explicitly.
- The project is still on the legacy compiled format (`.conventions/conventions.md`) and you want to migrate to the new `index.md` + `manifest.yaml` layout.
- You simply want to regenerate the bundle from scratch.

The new format references `ai-ressources/` source files directly, so there is **no staleness check** — running this command always rebuilds the bundle when invoked with `--full` (the default semantics).

```mermaid
flowchart TD
    START(["/spec-refresh-conventions"]) --> GUARD{".specs/\nexists?"}
    GUARD -->|no| ABORT["Abort — run /spec-init first"]
    GUARD -->|yes| STACK{".specs/stacks/\n_default.md?"}
    STACK -->|missing| NOSTACK["Skip — no stack defined"]
    STACK -->|exists| LEGACY{"Legacy\nconventions.md\nfound?"}
    LEGACY -->|yes| MIGRATE["Migrate: delete legacy\nfile, continue"]
    LEGACY -->|no| SIGNALS["Extract stack signals\n(typescript, bun, react, ...)"]
    MIGRATE --> SIGNALS
    SIGNALS --> REFRESH["/conventions.refresh --full\n(writes index.md + manifest.yaml)"]
    REFRESH --> REPORT["Verbose report"]
    NOSTACK --> REPORT
    ABORT --> REPORT
    REPORT --> DONE(["Done"])

    style START fill:#e8f4f8,stroke:#2196F3
    style DONE fill:#e8f5e9,stroke:#4CAF50
```

---

## Steps

### Step 1 — Guard

Verify `.specs/` directory exists. If not:

> This project has not been initialized with LiveSpec. Run `/spec-init` first.

Stop.

### Step 2 — Legacy detection

If `.conventions/conventions.md` (compiled legacy format) exists:

- Report: `Legacy compiled-format detected — migrating to index.md + manifest.yaml.`
- Delete `.conventions/conventions.md` (the new format supersedes it).
- Continue to Step 3.

### Step 3 — Extract Signals from Stack

**Read** `.specs/stacks/_default.md` fully. **Read** `.specs/project.md` if it exists.

Extract a flat list of keyword signals: technology names, dependency names, architecture keywords, project type keywords, platform keywords. These are **raw signals** — do not attempt to map them to convention domains yourself.

Example: for a Bun + TypeScript + cron-parser project → `typescript, bun, cron-parser, parseArgs, cli`

### Step 4 — Run Bootstrap Path

**Read** [`~/.claude/livespec/references/conventions-sync.md`](~/.claude/livespec/references/conventions-sync.md) and follow its **Bootstrap Path** algorithm. Invoke `/conventions.refresh --full` and pass the extracted signals from Step 3 so the skill can resolve them via `domain-catalog.md` in ai-ressources.

The skill writes:

- `.conventions/index.md` — routing table (sub-domains + `→ $AIRESOURCES/...` lines)
- `.conventions/manifest.yaml` — machine-readable mirror

No compiled `conventions.md` is produced.

### Step 5 — Verbose Report

Display a verbose report on stdout, regardless of the outcome:

```
Conventions Bootstrap Report
════════════════════════════

  Stack file:           .specs/stacks/_default.md
  Stack updated:        2026-05-17
  Signals extracted:    typescript, bun, react, cloudflare, ...
  Legacy file removed:  yes | no
  Sub-domains written:  code, design-tokens, design-components, design-views
  Files referenced:     12

  Result: Conventions bundle generated at .conventions/index.md + .conventions/manifest.yaml
```

If the bundle already existed and `--full` rebuilt it:

```
  Result: Conventions bundle regenerated (full rebuild)
```

If no stack file:

```
  Status: NO STACK
  Action: None — run /spec-init to define a stack
```

### Step 6 — Flags

| Flag | Behavior |
|------|----------|
| `--full`, `-F` | Default. Always rebuild `.conventions/index.md` + `.conventions/manifest.yaml` from scratch by re-detecting sub-domains. |
| `--force`, `-f` | Alias of `--full`. Kept for backward compatibility. |
| `--dry-run`, `-d` | Show what would happen without writing any file. |

If `--dry-run` is passed, run Steps 1-3 and display the report at Step 5, but do not invoke `/conventions.refresh --full` and do not delete any legacy file.

---

## Output

- Verbose report on stdout (always).
- `.conventions/index.md` + `.conventions/manifest.yaml` created or rewritten (unless `--dry-run` or no stack file).
- Legacy `.conventions/conventions.md` deleted if it was present.

---

## Definition of Done

- [ ] Guard checks `.specs/` existence.
- [ ] Legacy `.conventions/conventions.md` migrated (deleted) when present.
- [ ] Stack signals extracted from `.specs/stacks/_default.md` (+ `.specs/project.md` if it exists).
- [ ] Bootstrap Path from `conventions-sync.md` followed and `/conventions.refresh --full` invoked.
- [ ] `.conventions/index.md` AND `.conventions/manifest.yaml` exist after execution (unless `--dry-run` or missing stack).
- [ ] Verbose report displayed with signals, legacy status, sub-domains, file count.
- [ ] `--dry-run` produces the report without writing files.
- [ ] Works when no stack file exists (clean abort, no error).

---

*LiveSpec Command v1.0*

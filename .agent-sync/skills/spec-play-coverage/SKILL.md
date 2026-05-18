---
name: spec-play-coverage
description: Migrated Claude command /spec-play-coverage
---

# /spec-play-coverage

---
description: "Open spec coverage playground with live grep data"
argument-hint: "[feature-name]"
---

<!-- Anti-drift block injected via @import (Chantier 1, AUDIT.md). See system/anti-drift-block.md for the canonical 6-field step shape, ERROR/BLOCKED line formats, and timeout/retry policy. -->
<!-- @import system/anti-drift-block.md -->


# Command: /spec-play-coverage

> Launch the Spec Coverage playground in a browser, pre-loaded with `@spec` anchor data from the codebase.

---

```mermaid
flowchart LR
    RESOLVE["Resolve\nfeature"] --> DETECT["Auto-detect\nsource dir"]
    DETECT --> SCRIPT["Run\nplay-coverage.sh\n(grep @spec anchors)"]
    SCRIPT --> BROWSER["Open playground\nin browser"]

    style RESOLVE fill:#e8f4f8,stroke:#2196F3
    style BROWSER fill:#e8f5e9,stroke:#4CAF50
```

---

## Steps

### Step 1 — Resolve Feature

1. If feature name provided as argument: find `.specs/features/NNN-feature-name/`
2. If no feature name: detect from current git branch (`feature/NNN-feature-name`)
3. If still ambiguous: list all features and ask user to choose

Store the resolved feature directory name (e.g. `004-notifications`).

### Step 2 — Auto-detect Source Directory

Check for common source directories at project root: `app/`, `src/`, `lib/`, `packages/`.

- If exactly one exists: use it
- If multiple exist: run `grep -rn "@spec FR-" <dir>/` on each, pick the one with matches
- If none exist or no matches: fall back to `.`

### Step 3 — Run Script

Resolve the script path and run it:

```bash
SCRIPT=$(dirname "$(readlink ~/.claude/.agent-sync/skills/spec-play-coverage/SKILL.md)")/../scripts/play-coverage.sh
bash "$SCRIPT" <FEATURE> <SOURCE_DIR>
```

Replace `<FEATURE>` with the resolved feature name and `<SOURCE_DIR>` with the detected source directory.

The script handles grep, JSON encoding, base64, and browser opening. Do **not** attempt to do these steps manually.

---

*LiveSpec Command v1.0*

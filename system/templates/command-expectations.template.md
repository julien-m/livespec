<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-001) -->
<!-- @spec(FR-001) -->

<!-- @spec FR-001: Enriched template — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-001 -->
<!-- @spec FR-002: Sections 1-11 enrichment — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-002 -->
---
command: <name>
contract_version: "1.0"
last_reviewed: YYYY-MM-DD
---

# Expectations — /spec.<name>

> Canonical contract for `/spec.<name>`. This file is the **operator contract**.
> A reader who has never run the command must be able, after reading sections 1-13,
> to describe expected console output, produced files, and the action to take in each
> outcome. Section 12 is the **machine contract** (YAML) consumed by
> `livespec verify-output`. Section 13 is the **demo session** — concrete examples
> with placeholders that `livespec verify-output --preview` instantiates against the
> current project.

## 1. Purpose

**One-line summary:** <one sentence describing what the command achieves>.

**Why it exists:** <2-3 lines on the problem this command solves and for whom>.

**Audience:** <human operator / CI / automated agent / mix>.

## 2. Preconditions

**Required state:**
- `<file or state required before invocation>`
- `<another precondition>`

**Recommended state (warning if missing):**
- `<state that improves outcome but is not strictly required>`

**Inputs:**
- `<positional arg>` — type, semantics, example.
- `--flag` — purpose, default, accepted values.

## 3. Observable Signals

**stdout must_contain:**
- `"<marker emitted on happy path>"` — proves <what step>
- `"<another marker>"` — proves <what>

**stdout must_not_contain:**
- `"Traceback"` — silent crash detector
- `"<failure marker>"`

**stderr:**
- `"<expected stderr line, or 'none'>"`

**Progress indicators:** <describe any spinner, percentage, or stage logs the user will see>.

## 4. Filesystem Effects

**create:**
- `<path>` — purpose, format.

**update:**
- `<path>` — what is changed and why.

**optional:**
- `<path that may or may not be touched>` — condition for creation.

**forbidden:**
- `<path that must NOT change>` — rationale (e.g. read-only zone, owned by another command).

## 5. Git Effects

**expected dirty paths:**
- `<staged or modified path>`

**forbidden changes:**
- `<path that must remain clean>`

**commit expectations:**
- `<commit message marker or 'none'>`

## 6. Produced Artifacts

- **path:** `<path>`
  - **purpose:** <what this file is for>
  - **format:** <Markdown / JSON / YAML / text>
  - **must_contain_sections:**
    - `"<section header expected in the artifact>"`

## 7. Exit Codes

| Code | Meaning | Operator action | Retry safe? |
|------|---------|-----------------|-------------|
| 0    | success | nothing | n/a |
| 1    | drift   | inspect report, fix discrepancy | yes after fix |
| 2    | blocked | check preconditions, retry | yes after fix |

## 8. Outcome Matrix

- **success:** all `must` rules pass, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0 (assertions diverge from contract)
- **blocked:** precondition missing or artifact missing (cannot evaluate)
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- **Typical range:** `<lo>`–`<hi>` seconds
- **Drivers:** <repo size, network calls, feature count…>
- **Cold vs warm:** <if applicable, contrast first run with cached>

## 10. Post-run Checks

- [ ] `<human check 1 — what to read first in the output>`
- [ ] `<human check 2 — what file to open next>`
- [ ] `<human check 3 — what to do before re-running>`

## 11. Troubleshooting

- **Symptom:** `<observed bad behavior>`
  - **Cause:** `<root cause>`
  - **Fix:** `<command or file edit>`
  - **Why it happens:** <2-line explanation of the underlying mechanic>

- **Symptom:** `<second observed bad behavior>`
  - **Cause:** `<root cause>`
  - **Fix:** `<command or file edit>`

## 12. Verify Contract

```yaml
verify:
  # Placeholders resolved at evaluation time:
  #   <feature>  — active feature directory name (e.g. "001-foo")
  #   <date>     — run artifact timestamp date (YYYY-MM-DD); NEVER commit date
  #   <path>     — passthrough (no substitution) — used inside path templates
  #
  # Verbs: must / may / must_not — independent buckets, no short-circuit.
  # Rule kinds: contains | exists | exit_code | produces_artifact
  must:
    - exit_code: 0
    - contains: "<happy-path marker>"
    - exists: ".specs/features/<feature>/spec.md"
  may:
    - contains: "<optional informational marker>"
  must_not:
    - contains: "Traceback"
  # Conditional branches activated when the run artifact's `flags` array
  # contains the declared flag. Multiple matching branches accumulate
  # (logical AND with base rules).
  when:
    - flag: "--visual"
      must:
        - contains: "Visual baselines updated"
        - exists: ".specs/features/<feature>/baselines/"
    - flag: "--json"
      must:
        - contains: "\"command\":"
```

## 13. Demo Session

> Concrete examples of what running the command looks like on a real project.
> Placeholders `<feature>`, `<screen>`, `<stack>`, `<path>` are substituted by
> `livespec verify-output --preview` against the cwd's `.specs/` data.
> Each sub-section must contain ≥ 3 non-empty content lines.

### Live Console Output

```
$ livespec <name> <args>
> Stage 1: <what the user sees first>
> Stage 2: <next visible line>
> Stage 3: <conclusion line>
exit 0
```

### Files Produced

```
.specs/
└── features/
    └── <feature>/
        ├── spec.md        # purpose of this file
        ├── plan.md        # purpose of this file
        └── progress.md    # purpose of this file
```

### Aligned / Drift / Missing

- **Aligned:** <what success looks like — observable signals all green, exit 0, operator does nothing>.
- **Drift:** <what a divergence looks like — which marker is missing, which file is unexpected, which exit code>.
- **Missing:** <what blocked looks like — which precondition was not met, which recovery command unblocks>.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Cold (first run) | <lo>–<hi>s | <factor> |
| Warm (cached) | <lo>–<hi>s | <factor> |
| Large repo | <lo>–<hi>s | <factor> |

### Edge Cases

- **<edge case 1>:** <what happens, what the user sees>.
- **<edge case 2>:** <what happens, what the user sees>.
- **<edge case 3>:** <what happens, what the user sees>.

### Post-run Actions

- **On success:** <next command to run, file to open, decision to make>.
- **On drift:** <how to inspect the report, fix the divergence, re-run>.
- **On blocked:** <which precondition to restore, which command to run first>.

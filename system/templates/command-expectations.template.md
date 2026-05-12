<!-- @spec FR-001: Template file — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-001 -->
---
command: <name>
contract_version: "1.0"
last_reviewed: YYYY-MM-DD
---

# Expectations — /spec.<name>

> Canonical contract for `/spec.<name>`. Fill every section below. Keep prose
> short and observable — every line must be checkable by a human or by the
> machine-readable `verify:` block at the bottom.

## 1. Purpose

One sentence describing what the command achieves for the operator.

## 2. Preconditions

- `<file or state required before invocation>`
- `<another precondition>`

## 3. Observable Signals

**stdout must_contain:**
- "<marker emitted on happy path>"

**stdout must_not_contain:**
- "Traceback"
- "<failure marker that must never appear>"

**stderr:**
- "<expected stderr line, or 'none'>"

## 4. Filesystem Effects

**create:**
- `<path>`

**update:**
- `<path>`

**optional:**
- `<path that may or may not be touched>`

**forbidden:**
- `<path that must NOT change>`

## 5. Git Effects

**expected dirty paths:**
- `<staged or modified path>`

**forbidden changes:**
- `<path that must remain clean>`

**commit expectations:**
- `<commit message marker or none>`

## 6. Produced Artifacts

- path: `<path>`
  must_contain_sections:
  - "<section header expected in the artifact>"

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix discrepancy |
| 2    | blocked | check preconditions, retry |

## 8. Outcome Matrix

- **success:** all `must` rules pass, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0 (assertions diverge from contract)
- **blocked:** precondition missing or artifact missing (cannot evaluate)
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- Typical range: `<lo>`–`<hi>` seconds
- Factors: `<repo size, network calls, feature count…>`

## 10. Post-run Checks

- [ ] `<human check 1>`
- [ ] `<human check 2>`

## 11. Troubleshooting

- **Symptom:** `<observed bad behavior>`
  **Cause:** `<root cause>`
  **Fix:** `<command or file edit>`

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

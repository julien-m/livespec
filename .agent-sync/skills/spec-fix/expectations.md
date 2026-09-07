---
command: spec-fix
contract_version: "1.0"
last_reviewed: 2026-09-07
---

<!-- @spec(FR-004) -->

# Expectations — /spec-fix

## 1. Purpose

Fix implementation gaps from /spec-check — functional and visual corrections.

## 2. Preconditions

- `A recent `checks/<date>-check.md` exists with non-empty findings.`

## 3. Observable Signals

**stdout must_contain:**
- "fix"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

The create/update and post-run repair effects below apply only to executable feature repairs. Preview (--dry-run/-d or read-only audit) loads an existing gap report or scans in memory, never invokes the writing spec-check or refreshes conventions; absent usable inputs block with an explicit recovery outside preview. Conventions mode uses only its debt workflow; collection parents delegate scoped child repairs. Runtime goal/receipt bookkeeping retains its existing protocol; it is not a business artifact write.

**create:**
- _(none)_

**update:**
- `src/`
- `.specs/features/<feature>/implementation.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `src/`

**forbidden changes:**
- `.specs/features/<feature>/spec.md`

**commit expectations:**
- `fix(<feature>): close gap`

## 6. Produced Artifacts

<!-- @spec FR-004: Proof docs — .specs/features/067-visual-preview-proof-publishing/spec.md#fr-004 -->
- stdout marker: `![visual proof](/absolute/path/to/image.png)` for each touched validation PNG
- stdout marker: `visual-preview url /absolute/path/to/image.png`
- stdout marker: `Open for annotation: http://127.0.0.1:<port>/i/<id>`
- fallback marker: `Visual preview: unavailable - visual-preview CLI missing`
- proof boundary: `visual_evidence_receipt_path` remains required for pixel fidelity; preview URLs are human-visible annotation proof only

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |
| 6    | visual gate FAIL after fix | iterate; do not mark done |
| 7    | visual gate BLOCKED (prereqs missing) | generate prereqs first, retry |

## 7b. Visual Gate (required after every visual fix)

`/spec-fix` MUST call `livespec visual-gate validate --feature <slug> --command spec-fix [--target <t>]` after applying any CSS / JSX / SwiftUI / Maestro / Tauri fix touching a visual feature. The skill MUST NOT report `done` while the gate exit code is non-zero.

When the gate exits 7 because mockups / baselines / Penflow trees / compare reports are missing, `/spec-fix` MUST generate the prerequisites (or surface them to the user) BEFORE touching code — fixing without baselines is the failure mode this gate exists to stop.

Nested invocation: any call back into `/spec-check` runs through an independent sub-agent so the active `/spec-fix` goal is not violated.

## 8. Outcome Matrix

- **success:** every `must` rule passes, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0
- **blocked:** precondition missing or artifact missing
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- Typical range: 30–900 seconds
- Factors: Number of findings, fix complexity

## 10. Post-run Checks

- [ ] Re-running /spec-check shows the gap closed

## 11. Troubleshooting

- **Symptom:** No findings to act on
  **Cause:** Stale check
  **Fix:** Re-run /spec-check first

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "fix"
    - receipt_verdict: {"kind": "conventions", "verdict": "PASS", "required_if_exists": true}
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-fix <feature>
> Reading checks/<date>.md → 3 issues
> Issue 1/3: visual drift on <screen> → re-rendering component
> Issue 2/3: missing @spec anchor on src/api/foo.ts:45
> Issue 3/3: unmapped FR-008 → added stub test
> All issues addressed — re-run /spec-check to verify
exit 0
```

### Files Produced

```
src/<modified files>
tests/<new or modified tests>
.specs/features/<feature>/implementation.md   # anchors refreshed
```

### Aligned / Drift / Missing

- **Aligned:** every issue from the gap report has a corresponding patch; re-running /spec-check returns 0. Exit 0.
- **Drift:** some issues could not be auto-fixed; the report lists them as `manual`. Exit 1.
- **Missing:** no gap report under `.specs/features/<feature>/checks/`. Exit 2 with recovery `/spec-check first`.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Few small issues | 30–90s | LLM call count |
| Visual drift (multi-screen) | 60–300s | re-render cost |
| Many structural issues | 120–600s | per-issue patch loop |

### Edge Cases

- `--dry-run`: shows the patch plan without writing business files, including gap reports or conventions bundles; existing protocol bookkeeping remains separate.
- Visual fix needs a design mockup change: fix flags it as `manual — update design source`.
- Auto-fix produces a regression in another test: fix rolls back and surfaces the conflict.

### Post-run Actions

- **On executable repair success:** re-run `/spec-check <feature>` to confirm zero gaps; preview returns its plan without running that writer.
- **On drift:** address the `manual` issues by hand, re-run `/spec-fix`.
- **On blocked:** run `/spec-check <feature>` to generate the gap report.


## Requirement evidence integrity (078 policy2)

- **Read** [review and progression](../../../system/review-protocol.md): every feature code/test edit and retry requires current Clarify/Analyze via `livespec validate <feature-dir> --progression implement --model <resolved-model>`, forwarding any explicit `--review-max-chars` budget and the same identity to child commands.
- Require actual mapped runner `execution_receipt_path` for applicable fix verification; prose and identifiers do not prove tests. **Read** [execution rules](../../../system/testing/execution-rules.md).
- Unfiltered feature repair requires all execution ACs AND declared documentary review ACs at prove/archive/verify-output. Filtered `--fr`/`--ac`/`--visual`/`--functional` repair certifies only actual mapped execution; unknown or open gaps outside the filter prohibit full feature status promotion.
- `--dry-run`/read-only audit performs no application edits and acquires no readiness/runtime obligation. `--conventions` retains its independent conventions proof; functional changes must re-enter feature readiness. Collection `--all` delegates feature goals with the same model/budget, removes the collection flag in children and inspects their actual results.
- Existing immutable historical contracts retain their original proof policy. Current policy2 receipts, scopes and review identities remain bound to their complete immutable contract at all three boundaries.

- Filtered AC/FR tasks freeze the selected declared execution ACs and current normative source; unrelated passing assertions, unknown selectors, absent/ambiguous FR links and stale selection fail closed. Review ACs require the existing complete verification. Preview/batch/conventions inventories exclude feature code/test/artifact writes and feature finalization; batch children retain their applicable tasks.

- Visual applicability follows the existing compiler: `visual` requires an executable feature fix. In --dry-run/-d, read-only audit, conventions-only and collection --all/-A, visual inspection and mutation rows are inactive; none requires capture, cleanup, baseline promotion or visual artifact updates. Normal visual repairs retain every existing visual gate.

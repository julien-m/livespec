# SHIP_RESULT Contract

> Canonical return contract emitted by `/spec-feature` when called by `/spec-ship`. Drives the merge / branch-delete decision in the ship orchestrator.
>
> Implementation: [`validator/contracts.py`](../../validator/contracts.py) (`ShipResult`, `parse_ship_result`).
>
> **@spec FR-002:** SHIP_RESULT JSON schema — [`.specs/features/014-supervisor-contracts/spec.md#fr-002`](../../.specs/features/014-supervisor-contracts/spec.md#fr-002)
> **@spec FR-005:** Regex-anchored parser — [`spec.md#fr-005`](../../.specs/features/014-supervisor-contracts/spec.md#fr-005)

---

## Schema

```jsonc
{
  "status":              "OK" | "BLOCKED",  // required
  "feature_slug":        "NNN-name",        // required, matches identity SLUG_REGEX
  "branch":              "feature/NNN-name", // required, non-empty
  "files_changed_count": integer,            // required, >= 0
  "timestamp":           "YYYY-MM-DDTHH:MM:SS",  // required, ISO 8601 prefix
  "commit_hash":         "string" | null,    // optional, present on status=OK
  "error":               "string" | null,    // optional, present on status=BLOCKED
  "run_artifact":        "string" | null     // child pipeline's spec-feature .specs/.runs/ artifact (059 AC-011)
}
```

`extra: forbid` — unknown keys reject the block.

## Wire format

```
⟪SHIP_RESULT_START_e9c4d1f7⟫
{
  "status": "OK",
  "feature_slug": "013-state-model-identity-resolution",
  "branch": "feature/013-state-model-identity-resolution",
  "files_changed_count": 13,
  "timestamp": "2026-05-04T15:32:18",
  "commit_hash": "c99d3f6b2",
  "error": null,
  "run_artifact": ".specs/.runs/spec-feature-2026-06-11T10-00-00.000000-e9c4d1f7.json"
}
⟪SHIP_RESULT_END_e9c4d1f7⟫
```

## Critical safety property

**`/spec-ship` MUST NOT invoke `livespec git merge` or `livespec git delete <branch>` until the SHIP_RESULT is parsed AND validated AND the child run artifact re-verifies as `success`.**

Without this gate, a malformed result (or an injected fake) could trigger a merge/delete on the wrong branch. The parser is the single point of text validation; merge/delete are gated on ALL of:

1. `result.status == "OK"` AND `result.branch == "feature/<resolved-slug>"` (existing gate).
2. `result.run_artifact` is non-null and `livespec verify-output spec-feature --run <result.run_artifact> --json` re-evaluates to `verify_result.outcome == "success"` (059 AC-011/AC-012). The artifact path is **only a pointer, never a verdict** — the trust decision derives from independently re-evaluating the on-disk artifact.
3. The artifact's `command` is `spec-feature` and its `feature` equals `result.feature_slug` (foreign/stale artifacts are Blocked).

`status: OK` with a null/absent/unreadable/malformed `run_artifact`, or a non-success machine outcome, marks the feature **Blocked** in `ship.md` — an OK without a verifiable artifact is not trusted. `status: BLOCKED` is never overturned by a passing artifact (artifact backing demotes, never promotes — EC-007).

## Parser behaviour

Identical to PHASE_RESULT: scans last 30 lines, last matching pair wins, JSON body validated against `ShipResult`. Legacy key-value blocks are also tolerated for compatibility with older agent prompts; `RUN_ARTIFACT:` maps to `run_artifact` and blank/missing values normalize to `null`.

## Caller behaviour

```python
from validator.contracts import parse_ship_result, ContractParseError, ContractValidationError

try:
    result = parse_ship_result(agent_stdout)
except (ContractParseError, ContractValidationError) as exc:
    print(f"BLOCKED at step ship - state_invalid - SHIP_RESULT invalid: {exc}")
    sys.exit(1)

if result.status != "OK":
    print(f"BLOCKED at step ship - state_invalid - {result.error}")
    sys.exit(1)

if result.branch != f"feature/{result.feature_slug}":
    print(f"BLOCKED at step ship - state_invalid - branch/slug mismatch")
    sys.exit(1)

# Safe to delete now
subprocess.run(["livespec", "git", "delete", result.branch], check=True)
```

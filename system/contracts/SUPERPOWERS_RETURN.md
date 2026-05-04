# SUPERPOWERS_RETURN Contract

> Canonical return contract emitted by Superpowers subagents (implementer / documenter / verifier) and consumed by `livespec-supervisor` at each checkpoint.
>
> Implementation: [`validator/contracts.py`](../../validator/contracts.py) (`SuperpowersReturn`, `parse_superpowers_return`).
>
> **@spec FR-003:** Superpowers return contract schema — [`.specs/features/014-supervisor-contracts/spec.md#fr-003`](../../.specs/features/014-supervisor-contracts/spec.md#fr-003)

---

## Schema

```jsonc
{
  "files":        ["src/foo.py", "tests/test_foo.py", ...],   // string[], may be empty
  "fr_ac": [
    {
      "number":  1,                       // FR or AC number, >= 1
      "mapping": { ... }                  // free-form: {"file": "...", "lines": "12-45", ...}
    },
    ...
  ],
  "test_results": {
    "passed":  integer,                   // >= 0
    "failed":  integer,                   // >= 0
    "skipped": integer                    // >= 0
  },
  "duration_ms": integer                  // >= 0
}
```

`extra: forbid` on every nested model.

## Wire format

```
⟪SUPERPOWERS_RETURN_START_b7d2e8a4⟫
{
  "files": [
    "src/auth/login.ts",
    "src/auth/login.test.ts"
  ],
  "fr_ac": [
    {"number": 1, "mapping": {"file": "src/auth/login.ts", "lines": "12-45"}},
    {"number": 2, "mapping": {"file": "src/auth/login.test.ts", "lines": "1-30"}}
  ],
  "test_results": {"passed": 12, "failed": 0, "skipped": 1},
  "duration_ms": 24580
}
⟪SUPERPOWERS_RETURN_END_b7d2e8a4⟫
```

## Critical safety property

`livespec-supervisor` MUST validate the Superpowers return BEFORE writing the per-step checkpoint to `progress.md`. Without this gate, a missing `duration_ms` or a malformed `test_results` block would corrupt the state file and break `--resume`.

The supervisor's behaviour on validation failure is to mark the step `Blocked` (with the parser error in the `reason` field) and halt per the Chantier 4 hard-halt-on-Blocked rule.

## Parser behaviour

Identical anchoring as PHASE_RESULT and SHIP_RESULT: last-30-lines window, last matching pair wins.

## Caller behaviour

```python
from validator.contracts import parse_superpowers_return, ContractParseError, ContractValidationError

try:
    result = parse_superpowers_return(superpowers_stdout)
except (ContractParseError, ContractValidationError) as exc:
    # Mark step Blocked, halt loop (Chantier 4)
    write_progress_blocked(step, reason=f"Superpowers return invalid: {exc}")
    print(f"BLOCKED at step {step} - state_invalid - Superpowers return invalid")
    sys.exit(1)

# Safe to checkpoint
write_progress_done(step, files=result.files, tests=result.test_results)
```

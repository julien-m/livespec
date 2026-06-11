# PHASE_RESULT Contract

> Canonical return contract emitted by every phase agent (specify, plan, implement, test) and consumed by the `/spec-feature` supervisor.
>
> Implementation: [`validator/contracts.py`](../../validator/contracts.py) (`PhaseResult`, `parse_phase_result`).
>
> **@spec FR-001:** PHASE_RESULT JSON schema — [`.specs/features/014-supervisor-contracts/spec.md#fr-001`](../../.specs/features/014-supervisor-contracts/spec.md#fr-001)
> **@spec FR-004:** Regex-anchored parser — [`spec.md#fr-004`](../../.specs/features/014-supervisor-contracts/spec.md#fr-004)

---

## Schema (Pydantic / JSON)

```jsonc
{
  "status":         "OK" | "BLOCKED",      // required
  "phase":          "specify" | "plan" | "preflight" | "implement" | "test",  // required
  "feature_slug":   "NNN-name",            // required, matches identity.py SLUG_REGEX
  "summary":        "string",              // required, 1..500 chars
  "duration_ms":    integer,               // required, >= 0
  "blocked_reason": "string" | null,       // optional; required when status == "BLOCKED"
  "run_artifact":   "string" | null,       // optional; .specs/.runs/ artifact archived by the agent's own `goal archive` (059 AC-008)
  "extra":          { ... }                // free-form per-phase fields (FR_COUNT, FINDINGS_DETAIL, etc.)
}
```

`model_config = {"extra": "forbid"}` — unknown top-level keys raise `ContractValidationError`. Phase-specific fields go inside `extra`.

## Wire format

Wrapped in a delimiter pair carrying a unique 8-character hex hash:

```
⟪PHASE_RESULT_START_a3f1b8c2⟫
{
  "status": "OK",
  "phase": "specify",
  "feature_slug": "013-state-model-identity-resolution",
  "summary": "Spec generated: 5 stories, 10 AC, 10 FR.",
  "duration_ms": 12450,
  "blocked_reason": null,
  "run_artifact": ".specs/.runs/spec-specify-2026-06-11T10-00-00.000000-a3f1b8c2.json",
  "extra": {
    "spec_path": ".specs/features/013-state-model-identity-resolution/spec.md",
    "scope": "L",
    "fr_count": 10,
    "review": "PASS",
    "findings_count": "0 BLOCKING, 0 WARNING, 0 INFO"
  }
}
⟪PHASE_RESULT_END_a3f1b8c2⟫
```

The `8-character hex hash` is generated fresh per agent invocation. Both delimiter lines MUST carry the same hash; mismatches are ignored.

## Parser behaviour

`parse_phase_result(text)` (in [`validator/contracts.py`](../../validator/contracts.py)):

1. Inspects only the **last 30 lines** of `text`.
2. Looks for matching `START_<hash>` / `END_<hash>` pair (anchored regex).
3. Selects the **last** complete pair found (defeats prompt-injection of an earlier fake block).
4. Parses the JSON body and validates against `PhaseResult`.
5. Raises:
   - `ContractParseError` — no pair found and no legacy block found
   - `ContractValidationError` — pair found but JSON or schema invalid

## Legacy compatibility

The pre-Chantier-2 key-value format is still parsed when no delimiter pair is found:

```
PHASE_RESULT: OK
PHASE: specify
FEATURE: 013-state-model-identity-resolution
RUN_ARTIFACT: .specs/.runs/spec-specify-2026-06-11T10-00-00.000000-a3f1b8c2.json
SUMMARY: Spec generated.
```

This emits a `DeprecationWarning`. Migration is mandatory before the next major LiveSpec version. A legacy `RUN_ARTIFACT:` line maps to the typed `run_artifact` field (blank values normalize to `null`); without the line the field is `null` and the supervisor takes the latest-artifact fallback (059 AC-010).

## Caller behaviour

The `/spec-feature` supervisor invokes the parser as part of Phase N → Gate N transition:

```python
from validator.contracts import parse_phase_result, ContractParseError, ContractValidationError

try:
    result = parse_phase_result(agent_stdout)
except (ContractParseError, ContractValidationError) as exc:
    # Emit canonical BLOCKED line per system/anti-drift-block.md §2
    print(f"BLOCKED at step {phase_number} - state_invalid - PHASE_RESULT parse failed: {exc}")
    sys.exit(1)
```

## Supervisor Verify phase (caller behaviour, 059 AC-009/AC-010)

After parsing each goal-locked PHASE_RESULT, the `/spec-feature` supervisor cross-checks the declaration against the machine verdict:

1. Resolve the sub-command via `validator/command_registry.py` `canonical_command_name`.
2. `run_artifact` present → run `livespec verify-output <sub-command> --run <run_artifact> --json`. Absent → fall back to the lexicographically latest `.specs/.runs/<sub-command>-*.json`; none found → canonical `BLOCKED at step <N> - verification_failed - no run artifact for <sub-command>`.
3. Require both identities on the loaded artifact before any declared `OK` may continue: `artifact.command == resolved_sub_command` (EC-005) AND `artifact.feature == feature_slug` — a foreign-command or foreign-feature artifact (notably via the latest fallback) is `blocked` (`BLOCKED at step <N> - verification_failed - foreign feature artifact`).
4. Declared `OK` + machine outcome `success` (top-level `outcome` of the `--json` envelope) → continue. Declared `OK` + outcome `drift`/`error`/`blocked` → emit the canonical BLOCKED line, run `livespec pipeline update --status blocked`, never spawn the next phase. A declared `BLOCKED` is never overturned by a passing artifact (EC-006).

## Phase-specific extras

Each phase populates `extra` with its own conventional fields. These are NOT validated by the schema (intentional — they're advisory metadata for gates), but consumers should be defensive when reading them.

| Phase     | Conventional `extra` fields                                                                  |
|-----------|----------------------------------------------------------------------------------------------|
| specify   | `spec_path`, `scope` (S/M/L), `fr_count`, `review`, `findings_count`, `findings_detail`     |
| plan      | `plan_path`, `steps_count`, `review`, `findings_count`, `findings_detail`                    |
| preflight | `verdict` (READY/WARNINGS/BLOCKED)                                                            |
| implement | `files_changed`, `steps_done`, `tests_passed`, `tests_failed`                                |
| test      | `ac_coverage`, `tests_passed`, `tests_failed`                                                 |

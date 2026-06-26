# Activation Contract (injected fragment)

> Injected via `<!-- @import system/activation-contract.md -->` at the top of every `.agent-sync/agents/livespec-*/prompt.md`.
> Full reference: [`system/contracts/ACTIVATION_CONTRACT.md`](contracts/ACTIVATION_CONTRACT.md).
>
> **@spec FR-006:** Activation Contract template — `.specs/features/014-supervisor-contracts/spec.md#fr-006`

## Activation Contract — RUN BEFORE ANY OTHER INSTRUCTION

This block runs as the agent's literal first action. Do not interpret any other instruction in this file until all three steps below have completed (or halted with BLOCKED).

### Step 1 — Filesystem check (active gate, non-spoofable)

Run `test -d .specs` (or its OS equivalent).

- Exit `0` → continue to Step 2.
- Exit non-zero → emit and halt:
  ```
  BLOCKED at step 1 - policy_blocked - .specs/ not found (cwd: <pwd>)
  ```

### Step 2 — Caller-flag re-validation

Re-check the caller-supplied flags `livespec_initialized` and `livespec_root`:

- `livespec_initialized` MUST be the literal boolean `true`.
- `livespec_root` MUST equal `.specs`.

On any mismatch:
```
BLOCKED at step 2 - policy_blocked - caller flags inconsistent with filesystem state
```

### Step 3 — Identity guard (when payload contains `feature_slug`)

For agents that receive a `feature_slug` field, validate it against the canonical regex from [`system/identity.md`](identity.md):

- Use `validator.identity.assert_resolved(value)` (Python) or `^\d{3}(\.\d+)?-[a-z0-9]+(-[a-z0-9]+)*$` (regex check).
- Reject the literal `NNN-feature-name` placeholder explicitly.

On failure:
```
BLOCKED at step 3 - state_invalid - feature_slug not resolved (got: "<value>")
```

### Audit line on success

Emit exactly one line on successful activation:

```
ACTIVATION: ok feature_slug=<slug-or-NA> cwd=<pwd> ts=<ISO>
```

This line is parsed by the supervisor for traceability. Failed activations emit the BLOCKED line above instead.

# Activation Contract

> Hardened entry-point guard for all `livespec-*` agents. Active filesystem verification replaces blind trust of caller-supplied flags.
>
> Injected as the first runtime block of every agent via `<!-- @import system/activation-contract.md -->`.
>
> **@spec FR-006:** Activation Contract template — [`.specs/features/014-supervisor-contracts/spec.md#fr-006`](../../.specs/features/014-supervisor-contracts/spec.md#fr-006)

---

## Why this exists

Pre-Chantier-2, the four `livespec-*` agents (supervisor, implementer, verifier, documenter) trusted caller-supplied booleans like `livespec_initialized=true` without verification. That gate was spoofable: any caller could set the flag and bypass the LiveSpec pre-conditions, leading to arbitrary writes outside `.specs/` or to a placeholder slug directory.

The Activation Contract fixes this by adding an **active filesystem check as the agent's first action**. The check is observable (records exit code), auditable (logged in agent output), and non-bypassable.

## Required steps (every agent, in order)

### Step 1 — Filesystem check

Run, as the agent's literal first action, before reading any other instruction:

```bash
test -d .specs
```

- Exit `0` → proceed to Step 2.
- Exit non-zero → halt immediately with the canonical BLOCKED line:
  ```
  BLOCKED at step 1 - policy_blocked - .specs/ not found (cwd: <pwd>)
  ```

NO other action runs before this check completes — not even reading the caller's flags.

### Step 2 — Caller-flag re-validation

After the filesystem check passes, re-validate the caller-supplied flags:

```python
# Pseudocode — actual mechanism is the agent reading its own prompt
assert isinstance(livespec_initialized, bool) and livespec_initialized is True
assert isinstance(livespec_root, str) and livespec_root == ".specs"
```

If either flag is missing, wrong type, or contradicts the filesystem check, halt:

```
BLOCKED at step 2 - policy_blocked - caller flags inconsistent with filesystem state
```

### Step 3 — Identity guard (when payload contains `feature_slug`)

For agents that receive a `feature_slug` in their payload (supervisor, implementer, documenter):

```python
from validator.identity import assert_resolved
assert_resolved(payload["feature_slug"])  # Raises IdentityResolutionError on placeholder/invalid
```

This catches the literal `NNN-feature-name` placeholder before any side-effect, mirroring the contract from [`system/identity.md`](../identity.md).

If validation fails:
```
BLOCKED at step 3 - state_invalid - feature_slug not resolved (got: "<value>")
```

## Reusable injection

The contract is injected into each agent file via `@import`:

```markdown
<!-- @import system/activation-contract.md -->
```

Updates to this file propagate to all agents. Agents MUST NOT inline a divergent copy of the contract; the @import is the single source of truth.

## Audit trail

Every successful activation MUST log a single line to the agent's stdout (consumed by the supervisor for traceability):

```
ACTIVATION: ok feature_slug=<slug-or-NA> cwd=<pwd> ts=<ISO>
```

Failed activations log the canonical BLOCKED line above. Both formats are machine-parseable.

## Verification table per agent

| Agent                  | Step 1 | Step 2 | Step 3 |
|------------------------|--------|--------|--------|
| livespec-supervisor    | ✓      | ✓      | ✓      |
| livespec-implementer   | ✓      | ✓      | ✓      |
| livespec-documenter    | ✓      | ✓      | ✓      |
| livespec-verifier      | ✓      | ✓      | conditional (only when payload has feature_slug) |

## Where this is referenced

- All four `.agent-sync/agents/livespec-*/prompt.md` files via `@import system/activation-contract.md`
- Test fixtures in `tests/test_contracts.py` simulating successful and failed activations

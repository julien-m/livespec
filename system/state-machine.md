# Pipeline State Machine

> Single source of truth for the state values used in `pipeline.md`, `progress.md`, `ship.md`, `preflight.md`, and consumed by `livespec-supervisor`, `/spec-feature --resume`, and `/spec-ship --resume`.
>
> **@spec FR-003:** State machine reference document — [`.specs/features/013-state-model-identity-resolution/spec.md#fr-003`](../.specs/features/013-state-model-identity-resolution/spec.md#fr-003)

---

## States

| State        | Meaning                                                                  |
|--------------|--------------------------------------------------------------------------|
| `Pending`    | Phase/step is registered but not started.                                |
| `InProgress` | Phase/step has started; not yet finished. Likely interrupted if observed at startup. |
| `Done`       | Phase/step completed successfully.                                       |
| `Blocked`    | Phase/step explicitly halted. A non-empty `reason` field is required.    |

`Skipped` is a derived label used by some commands when a phase does not apply to the current feature (e.g., visual baselines for a backend-only feature). It is treated like `Done` for resume advancement.

## Allowed transitions

```
Pending ──► InProgress ──► Done
Pending ──► InProgress ──► Blocked ──► Pending  (after manual remediation)
Pending ──► InProgress ──► Blocked ──► InProgress (when --resume continues a fix-in-progress)
Pending ──► Skipped (terminal — does not advance to InProgress)
```

Forbidden transitions:
- `Done` → anything (terminal)
- `Skipped` → anything (terminal)
- `Pending` → `Done` (must pass through `InProgress`)

## Resume rules

`/spec-feature --resume` and `/spec-ship --resume` MUST:

1. Read the state file (`pipeline.md` for features, `ship.md` for ship batches).
2. Find the **first** phase/step in pipeline order whose state is NOT `Done` and NOT `Skipped`.
3. **If that state is `Blocked`** — do NOT advance. Emit:
   ```
   BLOCKED at step <phase> - state_invalid - phase marked Blocked at <timestamp>; reason: <reason>
   ```
   Stop. The user must clear the block manually before retrying.
4. **If that state is `Pending`** — spawn the corresponding phase agent fresh.
5. **If that state is `InProgress`** — spawn the corresponding phase agent with `--resume` in its instructions; the agent reads its sub-state file (typically `progress.md` for the Implement agent) to find the first non-Done step.

## `Blocked` requires a reason

Any state file that records `current_state: Blocked` MUST also carry a non-empty `reason` field. The `validator/state_files.py` validator rejects state files that violate this rule.

## Hard halt format

The canonical halt line (used by `livespec-supervisor`, `/spec-feature`, `/spec-ship`) is the BLOCKED format from [`system/anti-drift-block.md`](anti-drift-block.md) §2:

```
BLOCKED at step <N> - <subtype> - <one-line reason>
```

For state-machine halts, `<subtype>` is `state_invalid`. Other anti-drift subtypes (`policy_blocked`, `prerequisite_unmet`, `dependency_unmet`, `verification_failed`) do not apply to this gate.

## Where this is referenced

- `commands/spec-feature.md` § Resume — defines the per-phase state table and references this doc
- `agents/livespec-supervisor.md` § Hard-halt-on-Blocked — links here for the canonical state set
- `validator/state_files.py` — `ALLOWED_STATES` set is kept in sync with the table above

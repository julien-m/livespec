# Anti-Drift Block

> Reusable hardened-step template for all `commands/*.md` and `agents/livespec-*.md` files.
> Injected via `<!-- @import system/anti-drift-block.md -->` directive at the top of each target.
>
> Goal: standardise the *form* of every step (prerequisite, evidence, success, failure) so executors
> cannot silently skip, reorder, or lose state. This block addresses **Chantier 1 from AUDIT.md**
> and resolves the recurring "Top optimisations to apply" findings shared across all sections.
>
> **Scope:** standardises form only. Does NOT fix factual bugs, internal contradictions, or
> identity/state defects (those are addressed by Chantiers 2, 3, 4).

---

## 1. Per-step canonical shape (6 fields)

Every numbered step in a command or agent file should expose the following sub-fields. Implementers
may use Markdown headers, bullet lists, or inline prose, but each sub-field MUST be present and
verifiable.

```markdown
### Step N — <imperative verb + object>

**Prerequisite:** Step N-1 success criteria met. (Step 1 prerequisite is "None.")

**Required inputs:**
- <file paths, env vars, tools, credentials, prior step outputs>

**Action:**
<one specific, executable instruction. Include exact command or tool call when known.>

**Execution evidence:** (capture observable proof BEFORE proceeding)
- <command output snippet, file path, exit code, line count, hash, or other measurable artifact>

**Success criteria:** (verify before advancing to Step N+1)
- <observable condition 1>
- <observable condition 2>

**Failure handling:**
- Retry up to `max_retries` (see §3) if the failure is recoverable.
- On terminal failure, emit the canonical ERROR line (§2) and stop.
- Do NOT silently fall back, substitute, or proceed.
```

---

## 2. Canonical failure lines

All commands and agents MUST use these exact formats — no paraphrasing, no localisation.

### ERROR (recoverable or terminal command failure)

```
ERROR step=<N> type=<command_failed|timeout|missing_dependency|permission_denied|network_unavailable|missing_secret|policy_blocked|verification_failed> retry_count=<n> timed_out=<true|false> message="<exact error text, single line>"
```

- `step` — numeric step ID (matches the failing step's heading)
- `type` — chosen from the closed set above
- `retry_count` — number of retries attempted before giving up
- `timed_out` — boolean, true if the command exceeded `timeout`
- `message` — verbatim error from the underlying tool, escaped to fit one line

### BLOCKED (policy denial or unmet prerequisite)

```
BLOCKED at step <N> - policy_blocked - <one-line reason>
```

- Use `policy_blocked` as the sub-type when a tool/skill is denied by sandbox, hooks, or permissions.
- For other prerequisites (e.g., missing file expected by Step N), substitute `policy_blocked`
  with `prerequisite_unmet`, `dependency_unmet`, or `state_invalid` as applicable, while keeping
  the same shape.

After emitting BLOCKED, the executor MUST stop. It does NOT silently substitute alternate commands,
prompt the user (unless explicitly authorised), or skip ahead.

---

## 3. Deterministic policy

Unless a step explicitly overrides them, the following defaults apply to every command, tool call,
or subprocess executed inside a step:

| Setting | Default | Rationale |
|---------|---------|-----------|
| `timeout` | `90s` | Bounds runaway commands; aligns with workflow-apex defaults. |
| `max_retries` | `1` | One retry on transient failure; subsequent failure → ERROR + stop. |
| Retry backoff | None (immediate) | Avoids masking systemic issues; if backoff is needed, the step must declare it. |
| Concurrency | None within a step | Parallel tool calls are allowed only when the step explicitly states so. |

**Overrides** are valid only when the step's body declares them inline, e.g.:

```markdown
**Failure handling:**
- Override: `timeout=300s`, `max_retries=3` (LLM call may need longer warm-up).
```

---

## 4. Anti-drift rules (apply to every command and agent)

These rules are global. They override implicit assumptions; nothing in a step's prose can opt out
unless an explicit override is declared.

1. Execute steps in the exact numbered order. Do NOT reorder, parallelise, merge, or skip.
2. Do NOT start step N+1 until step N's `Success criteria` are observably met.
3. Do NOT assume a step is already done. Capture evidence (§1) before advancing.
4. Run listed commands as written. If denied by policy, emit BLOCKED (§2) and stop.
5. On terminal failure beyond `max_retries`, emit ERROR (§2) and stop. No silent substitution.
6. "Probably correct", "should work", "looks fine" are NOT success criteria. Replace with
   observable predicates before finalising the file.
7. In dry-run mode, do NOT mutate files, skills, tasks, or external systems. Output the proposed
   change and an explicit "no changes applied" line.
8. Activation Contracts (agents only) MUST run a filesystem check (e.g., `test -d .specs`) BEFORE
   trusting any caller-supplied flag (`livespec_initialized`, `livespec_root`, etc.). See
   Chantier 2 for the full return-contract specification.

---

## 5. Final consistency check (run before declaring DONE)

Before any command or agent reports `DONE`, verify the following programmatically (or via a
checklist when programmatic verification is unavailable):

- [ ] Every step in the file has the 6 fields from §1.
- [ ] Every failure path emits one of the canonical lines from §2.
- [ ] Every command call respects the policy from §3, or declares its override inline.
- [ ] Every "Success criteria" entry is observable (file path, exit code, hash, count, or quoted output).
- [ ] No `[NEEDS CLARIFICATION]`, `[ASSUMED]`, or `<placeholder>` tokens remain unresolved.
- [ ] Final report line is exactly `DONE` or `BLOCKED at step N - <one-line reason>` — no
      "should", "probably", or "hopefully".

If any checkbox fails, emit the corresponding ERROR/BLOCKED line and stop. Do NOT report DONE.

---

## 6. Drift tests (mini-suite for command/agent maintainers)

When introducing a new command or substantially modifying an existing one, run these scenarios:

1. **Reordering attempt** → executor jumps from Step 1 to Step 3. Expected: BLOCKED (Step 2
   prerequisite unmet).
2. **Skip-on-assumption** → executor declares Step N "obviously done" without evidence. Expected:
   BLOCKED (missing execution evidence).
3. **Policy-blocked command** → tool denied by sandbox. Expected: BLOCKED with `policy_blocked`.
4. **Timeout** → command exceeds `timeout`. Expected: ERROR with `type=timeout`, then stop.
5. **Missing dependency / permission / network / secret** → ERROR with corresponding `type`.
6. **Dry-run mutation attempt** → executor tries to write/edit/delete in dry-run. Expected:
   BLOCKED (mode is preview-only; no side effects).

These tests should live alongside the command (e.g., as an executable shell script or a checklist
in the command's `## Drift tests` section).

---

*This block is a form-standardisation tool. It does NOT replace command-specific business logic,
identity resolution (Chantier 4), supervisor↔subagent contracts (Chantier 2), or write-lock
semantics (Chantier 3).*

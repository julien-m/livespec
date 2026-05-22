<!-- @spec FR-011: Shared command runtime docs — .specs/features/052-deterministic-command-goal-contracts/spec.md#fr-011 -->

# Anti-Drift Block

> Reusable hardened-step template for all LiveSpec `.agent-sync` skills and agents.
> Injected via `<!-- @import system/anti-drift-block.md -->` directive at the top of each target.
>
> Goal: standardise the *form* of every step (the 6 canonical fields defined in §1) so executors
> cannot silently skip, reorder, or lose state. This block addresses **Chantier 1 from AUDIT.md**
> and resolves the recurring "Top optimisations to apply" findings shared across all sections.
>
> **Scope:** standardises form only. Does NOT fix factual bugs, internal contradictions, or
> identity/state defects (those are addressed by Chantiers 2, 3, 4).

---

## 1. Per-step canonical shape (6 fields)

Every numbered step in a command or agent file MUST expose the following 6 sub-fields, **using these
exact names as written**. They are the canonical labels — references in this block (§4, §5) and in
all reviews target these names verbatim. Implementers may use Markdown headers, bullet lists, or
inline prose, but each named sub-field MUST be present and observably verifiable.

| # | Canonical field name | Purpose |
|---|----------------------|---------|
| 1 | `Prerequisite` | What must be true before this step starts. |
| 2 | `Required inputs` | Files, env vars, tools, credentials, or prior-step outputs consumed. |
| 3 | `Action` | One specific, executable instruction (exact command or tool call when known). |
| 4 | `Execution evidence` | Observable proof captured BEFORE advancing (path, exit code, hash, line count, quoted output). |
| 5 | `Success criteria` | Observable conditions verified BEFORE moving to step N+1. |
| 6 | `Failure handling` | Retry policy + which canonical line (ERROR §2 or BLOCKED §2) to emit on failure. |

Reference template (use the names from the table above, do NOT rename them):

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

The BLOCKED line is **always 3 segments separated by ` - `**, with no exception. This single shape
is reused everywhere in this block (including §5's final report line):

```
BLOCKED at step <N> - <subtype> - <one-line reason>
```

- `<N>` — the failing step's numeric ID.
- `<subtype>` — chosen from this closed set:
  - `policy_blocked` — tool/skill denied by sandbox, hooks, or permissions.
  - `prerequisite_unmet` — a Step N-1 success criterion is not met.
  - `dependency_unmet` — a required input file/tool is missing.
  - `state_invalid` — pipeline/progress state is in an unexpected shape.
  - `verification_failed` — final consistency check (§5) failed.
- `<one-line reason>` — single-line, no quotes, ≤120 chars.

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

### Runtime goal contract

Before any slash command starts command-specific work, it MUST compile a deterministic runtime goal:

**Precheck:** Before rendering, verify no goal is already active in the platform. If you see `The active goal is...` or similar, emit the canonical BLOCKED line (§2 `prerequisite_unmet`) and instruct the user to run `/goal clear` first.

```bash
livespec goal render <command-name> --feature <feature-slug> --flags "<active-flags>" --save
```

This writes a task file to `.specs/.runs/goal-<command>-<hash8>.md` and prints:
```
hash:<full-sha256> | task-file:.specs/.runs/goal-<command>-<hash8>.md
```

- **Read the task file** — it contains every execution task as a checkbox `[ ]` and the full Definition of Done.
- **Immediately after rendering, emit the slash command `/goal`** with hash and file reference. Output exactly:
  ```
  /goal hash:<hash> | <command> for <feature> — task list: .specs/.runs/goal-<command>-<hash8>.md
  ```
  This compact form stays within the platform goal field character limit while preserving the full task list.
  This is mandatory — no flag bypasses it.
- **The task file is the active working list for this run.** Check `[ ]` → `[x]` after each task. You MUST:
  1. Execute tasks in order — no reordering, no skipping
  2. Capture observable evidence before checking each task (§1 form)
  3. Consult [`SKILL.md`](SKILL.md) phase descriptions for implementation detail — but do NOT treat SKILL.md sections as a sequential execution plan; the task file is authoritative
  4. If `--save` is unavailable or the task file has no tasks, fall back to the full render output (omit `--save`) and read the `Execution tasks (in order):` section
- The goal is compiled from machine-readable `expectations.md`, the command Definition of Done, normalized flags, and resolved feature state. It MUST NOT be rewritten or improvised by the LLM.
- If goal rendering fails, emit the canonical BLOCKED line (§2) and stop.
- If Claude Code does not accept the `/goal` command, emit the canonical BLOCKED line (§2) and stop.

Before any command or agent reports `DONE`, verify the following programmatically (or via a
checklist when programmatic verification is unavailable):

- [ ] Every step in the file has the 6 fields from §1.
- [ ] Every failure path emits one of the canonical lines from §2.
- [ ] Every command call respects the policy from §3, or declares its override inline.
- [ ] Every "Success criteria" entry is observable (file path, exit code, hash, count, or quoted output).
- [ ] No `[NEEDS CLARIFICATION]`, `[ASSUMED]`, or `<placeholder>` tokens remain unresolved.
- [ ] Final report line is exactly `DONE` or the canonical BLOCKED line from §2
      (`BLOCKED at step <N> - <subtype> - <one-line reason>`) — no "should", "probably", or "hopefully".

If any checkbox fails, emit the corresponding ERROR/BLOCKED line (using the §2 shape) and stop.
Do NOT report DONE. The subtype for a §5 failure is `verification_failed`.

### Runtime finalization gate

Before a slash command reports success, its observable stdout, stderr, exit code,
flags, cwd, git state, and filesystem effects MUST be recorded and verified via:

```bash
livespec run finalize --command <command-name> --exit-code <code> \
  --stdout-file <captured-stdout> --stderr-file <captured-stderr> --cwd <project-root>
```

If finalization returns `drift`, `blocked`, or `error`, the slash command MUST
emit the corresponding canonical ERROR/BLOCKED line and MUST NOT report success.
`/spec-verify-output` may verify itself only through an already-recorded wrapper
artifact to avoid recursive verification.

After finalization, run the deterministic goal gate with the same command, feature,
flags, and run artifact:

```bash
livespec goal verify <command-name> --feature <feature-slug> --flags "<active-flags>"
```

- `success` (exit 0): the command may report success.
- `drift` or `error` (exit 1): emit `ERROR step=<N> type=verification_failed ...` using the command's final step number and do not complete the goal.
- `blocked` (exit 2): emit `BLOCKED at step <N> - verification_failed - goal verification blocked` using the command's final step number and return a resumable status.
- Commands without feature context omit `--feature`; commands without active flags pass an empty flags string.

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

---

## 7. Hook & Integration Resolution (runtime)

You are currently executing a LiveSpec slash command. The user invoked you
via a literal `/spec-<NAME>` instruction (e.g. `/spec-plan`, `/spec-feature`).
Legacy `/spec.<NAME>` aliases are accepted during the naming migration.
This `<NAME>` is the canonical command name and is directly observable in
the user's invocation string.

At the VERY start of execution:

1. Read the slash-command invocation string from the current user turn.
2. Strip the leading `/spec-` prefix (or legacy `/spec.` prefix) to obtain `<NAME>`.
   - Valid example: `/spec-plan` → `<NAME>` = `plan`
   - Valid example: `/spec-feature` → `<NAME>` = `feature`
3. If you have a resolved feature slug (e.g., `042-notifications`), run:

       livespec hooks resolve --event before --command <NAME> --feature <slug>

   Otherwise (no feature context available), run:

       livespec hooks resolve --event before --command <NAME>

4. Treat stdout (if non-empty) as additional context to honor before
   proceeding with the command body.

At the VERY end of execution, run the same invocation with `--event after`,
optionally including `--feature <slug>` if available.

**Absence handling** (all conditions → silent no-op, never an error):

- the invocation does not match `/spec-<NAME>` or legacy `/spec.<NAME>` → skip resolution
- the CLI binary is not on PATH → skip resolution
- `--feature` is omitted when feature context is unavailable (absence-tolerant)
- stdout is empty → no injection
- exit code is non-zero → skip resolution and continue

### Chained / pipeline invocations

When `/spec-feature` (or `/spec-ship`) spawns subagents in sequence
(Specify, Plan, Implement, Test, …):

**Decision LOCKED — option β: per-sub-command resolution.** The hook
resolver always receives the name of the sub-command that is currently
executing — NOT the outer pipeline name. Implementation contract:

1. When the user invokes `/spec-feature`, the OUTER command resolves
   `before-feature` / `after-feature` at its outer boundary with
   `<NAME> = feature`.
2. Before spawning each subagent (Specify, Plan, Implement, Test, …),
   the supervisor in `.agent-sync/skills/spec-feature/SKILL.md` MUST prepend a synthetic
   invocation header to the subagent prompt, of the EXACT form:

       /spec-<subcmd>

   where `<subcmd>` ∈ {`specify`, `plan`, `implement`, `test`, …}. This
   single line is the FIRST line of the subagent's user turn, so the
   subagent applies steps (1)–(4) of this directive against `<subcmd>`,
   not `feature`. The same rule applies to `.agent-sync/skills/spec-ship/SKILL.md` (batch
   wrapper).
3. Each subagent therefore runs (with `--feature <slug>` included when feature
   context is available):

       livespec hooks resolve --event before --command <subcmd> [--feature <slug>]
       livespec hooks resolve --event after  --command <subcmd> [--feature <slug>]

   at its own boundaries — completely independent of the outer call.
4. Integrations target sub-phases by listing them explicitly in
   `commands:`. Example: `commands: [specify, plan]` injects at
   `before-specify` AND `before-plan` inside a `/spec-feature` pipeline,
   but NOT at `before-feature`. To inject at the outer pipeline boundary
   ONLY, list `[feature]`. To inject at BOTH outer and inner, list all
   relevant names explicitly. **No automatic propagation from outer to
   inner.** The `commands:` list is authoritative.

See [`integrations.md`](integrations.md) for the full Level 0 semantics
and [`hooks.md`](hooks.md) for the Level 1/2/3 algorithm.

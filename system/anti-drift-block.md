<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-004) -->
<!-- @spec(FR-011) -->
<!-- @spec(FR-001) -->
<!-- @spec(FR-019) -->

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

Every numbered step in a command or agent file exposes the following 6 sub-fields, **using these
exact names as written**. They are the canonical labels — references in this block (§4, §5) and in
all reviews target these names verbatim. Implementers may use Markdown headers, bullet lists, or
inline prose, but each named sub-field is present and observably verifiable.

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

Commands and agents use these exact formats (no paraphrasing, no localisation).

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

After emitting BLOCKED, the executor hands control back with what was tried and what is missing;
it does not silently substitute alternate commands or skip ahead.

---

## 3. Deterministic policy

Unless a step explicitly overrides them, the following defaults apply to every command, tool call,
or subprocess executed inside a step:

| Setting | Default | Rationale |
|---------|---------|-----------|
| `timeout` | `90s` | Bounds runaway commands; aligns with workflow-apex defaults. |
| `max_retries` | `2` | Three attempts in total; then ERROR or BLOCKED with a handback report. |
| Retry backoff | None (immediate) | Avoids masking systemic issues; if backoff is needed, the step must declare it. |
| Concurrency | None within a step | Parallel tool calls are allowed only when the step explicitly states so. |

**Overrides** are valid only when the step's body declares them inline, e.g.:

```markdown
**Failure handling:**
- Override: `timeout=300s`, `max_retries=3` (LLM call may need longer warm-up).
```

### Evidence-first retry contract

Before retrying any failed command, tool call, poll, or interactive write such as `write_stdin`, the
executor records one line with these fields:

```text
retry_hypothesis="<why the previous attempt failed>" retry_evidence="<observable proof to collect before retry>" retry_result="<PASS|FAIL|BLOCKED after retry>"
```

Rules:

- `retry_hypothesis` is a concrete failure theory, not "try again".
- `retry_evidence` names a measurable artifact, exit code, screen state, file path, timestamp, or
  command output required before the retry can count as progress.
- `retry_result` is filled after the retry and determines the next action: `PASS` continues,
  `FAIL` emits ERROR when retries are exhausted, and `BLOCKED` emits the canonical BLOCKED line.
- Repeating the same failing command without this record does not count as a retry.
- For polling or terminal interaction failures, prefer a fresh artifact, state file, timestamp, or
  post-prompt screen region over a stale screen line.

---

## 4. Anti-drift rules (apply to every command and agent)

These rules apply unless a step declares an explicit override.

1. Follow the numbered order; a step starts once the previous step's success criteria are observed.
2. Capture evidence (§1) instead of assuming a step is done.
3. Run listed commands as written. A policy denial emits BLOCKED (§2).
4. After `max_retries`, emit ERROR or BLOCKED (§2) with what was tried; no silent substitution.
5. "Probably correct" or "looks fine" are not success criteria; use observable predicates.
6. Dry-run mode mutates nothing and ends with an explicit "no changes applied" line.
7. Agents check the filesystem (e.g., `test -d .specs`) before trusting caller-supplied flags
   (`livespec_initialized`, `livespec_root`, etc.); see Chantier 2.

---

## 5. Final consistency check (run before declaring DONE)

<!-- @spec FR-009: Short outcome-based goal protocol — .specs/features/081-lightweight-outcome-goals/spec.md#fr-009 -->

### Runtime goal contract

A goal is required only for autonomous long runs: `/spec-ship`, `/spec-feature --auto`, `/spec-init --auto` (including `--from-code --auto`), `/spec-implement` without `--step`, and `/spec-*` children spawned with `--auto` by those runs. Other commands run directly; a goal stays optional. The contract field `goal_requirement` records which case applies.

1. Render once: `livespec goal render <command-name> [--feature <slug>] --flags "<active-flags>" --save`, adding `--model=<actual-model>` when the goal has review tasks and the model is resolved. It prints `hash:<sha256> | contract-file:<path> | state-file:<path>`; rendering the same goal again keeps its progress.
2. Read the contract file: `stop_condition` is the completion check; `tasks` are the few proofs that matter (hook context, QE analysis, typed execution/review receipts with acceptance mapping, visual and finalize receipts, one feature-scope conventions receipt, `outcome.verified`, `archive.run`); `checklist` is the skill inventory as guidance, not proven item by item.
3. Native goal: when the runtime offers one (Codex `create_goal`/`get_goal`/`update_goal`, Claude Code `/goal`), set it to `<command> for <feature>: <stop_condition.display> — contract-file:<path> — state-file:<path>`. If a goal is already active, update it when the tool allows; otherwise leave it untouched, warn and continue. Without native support, print one warning line and continue with the CLI contract.
4. Prove each required task once its receipt exists: `livespec goal prove --contract <contract-file> --state <state-file> --task <task-id> --evidence '<json>'`. Only `goal prove` changes task status; never edit the contract or state files.
5. `outcome.verified`: submit `{}`; the goal runs the stop condition itself (declared timeout override: 300 s) and accepts exit 0 with output.
6. `REJECTED_NEEDS_ACTION` lists the missing evidence and repair actions. After three rejections of the same task, prove returns `BLOCKED` with a `handback` (attempts, missing evidence): report it to the user and hand back control.
7. When inputs drift (feature slug, acceptance criteria, hook context, skill inventory), `goal prove` and `goal archive` recompile the contract in place, keep the evidence that still validates and report `recompiled`.
8. Close: archive the run, prove `archive.run` with the printed `.specs/.runs/` path, require `livespec goal status --state <state-file>` to show every task complete before `DONE`, then mark the native mirror complete (`update_goal`) when one exists. A time budget that expires after the stop condition passed does not block completion.

### Versioned evidence purpose

<!-- @spec FR-009: Typed evidence purpose — .specs/features/078-requirement-evidence-integrity/spec.md#fr-009 -->

- Task inventories declare `evidence_kind` (documentary, review, execution). Review proof requires current raw reviewer evidence (**Read** [the shared protocol](review-protocol.md)); execution proof requires the runner-owned receipt and reviewed acceptance scope (**Read** [execution rules](testing/execution-rules.md#execution-evidence)). Generic output cannot prove execution.
- Legacy archives keep their original policy; `.reviews/` holds disposable caches and the canonical Markdown stays authoritative.

### Transcript capture

<!-- @spec FR-009: Transcript capture protocol — .specs/features/059-pipeline-verify-phase/spec.md#fr-009 -->

Append key CLI output (`livespec validate`, `pytest`, `livespec finalize verify`) to `$TMPDIR/livespec-goals/transcripts/<command>-<hash8>.out/.err`, capturing the wrapped command status (not `tee`'s):

```bash
T="$TMPDIR/livespec-goals/transcripts"; mkdir -p "$T"
set -o pipefail; set +e
<cli command> 2>>"$T/<command>-<hash8>.err" | tee -a "$T/<command>-<hash8>.out"
cmd_status=${PIPESTATUS[0]}; set -e
```

- Pass `"$cmd_status"` to `livespec goal archive --exit-code`.
- Truncate files above `MAX_TRANSCRIPT_BYTES` (10 MiB) keeping the most recent bytes (EC-009); omit unreadable transcripts (EC-008); without transcripts, archive without `--stdout-file`/`--stderr-file` and `contains` rules report SKIP (AC-014, FR-010).

### Archive & prove archive.run

<!-- @spec FR-009: Archive-then-prove protocol — .specs/features/059-pipeline-verify-phase/spec.md#fr-009 -->

Every contract ends with `archive.run`:

```bash
livespec goal archive --contract <c> --state <s> [--feature <slug>] [--exit-code <n>] [--stdout-file <out>] [--stderr-file <err>]
livespec goal prove --contract <c> --state <s> --task archive.run --evidence '{"run_artifact_path": "<printed .specs/.runs/ path>"}'
```

`goal status` reports the goal complete only after this proof (EC-010); prose claims, exit codes and `$TMPDIR` paths are not substitutes.

### Internal Command Invocations

When a goal-bearing command needs another `/spec-*` command:

1. Spawn an independent native sub-agent; do not run the nested slash command inline or through a private CLI shortcut.
2. Fix its `cwd`/working directory to the resolved `project_root`; without a native cwd field, the prompt first runs `cd <project_root>` and **Read** [`../.specs/spec-system.md`](../.specs/spec-system.md).
3. The first executable prompt line is the literal nested command (for example `/spec-fix`); the child owns its own goal when its run requires one.
4. The parent reads only the child's structured result, artifacts and final status. Plain hints such as `Run /spec-plan next` are suggestions.

Each skill that mentions nested `/spec-*` calls includes a machine-readable section:

```markdown
## Internal Command Invocations

- [subagent] `/spec-fix <feature>` — executable nested command; resolve current LiveSpec `project_root`, run child with `cwd`/working directory=`project_root`; if native cwd is unavailable, child prompt must first `cd <project_root>` and **Read** [`../.specs/spec-system.md`](../.specs/spec-system.md) before command; child owns its goal.
- [suggestion] `/spec-plan <feature>` — displayed only as an operator next step; not executed by this command.
```

`livespec goal render` rejects executable `/spec-*` entries marked `inline`, `direct`, `cli`, `api` or any mode other than `subagent`/`suggestion`, and `[subagent]` rows that omit `project_root`, `cwd`/working directory, or **Read** [`../.specs/spec-system.md`](../.specs/spec-system.md).

### Before DONE

- [ ] Every step in the file has the 6 fields from §1.
- [ ] Every failure path emits one of the canonical lines from §2.
- [ ] Every command call respects the policy from §3, or declares its override inline.
- [ ] Every "Success criteria" entry is observable (file path, exit code, hash, count, or quoted output).
- [ ] No `[NEEDS CLARIFICATION]`, `[ASSUMED]`, or `<placeholder>` tokens remain unresolved.
- [ ] For goal runs: `livespec goal status` shows every task complete.
- [ ] Final report line is `DONE` or the canonical BLOCKED line from §2 (`BLOCKED at step <N> - <subtype> - <one-line reason>`), with what was tried and what is missing.

The subtype for a §5 failure is `verification_failed`.

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

When `/spec-feature` (or `/spec-ship`) spawns independent native sub-agents in sequence
(Specify, Plan, Implement, Test, …):

**Decision LOCKED — option β: per-sub-command resolution.** The hook
resolver always receives the name of the sub-command that is currently
executing — NOT the outer pipeline name. Implementation contract:

1. When the user invokes `/spec-feature`, the OUTER command resolves
   `before-feature` / `after-feature` at its outer boundary with
   `<NAME> = feature`.
2. Before spawning each independent native sub-agent (Specify, Plan, Implement, Test, …),
   the supervisor in [`../.agent-sync/skills/spec-feature/SKILL.md`](../.agent-sync/skills/spec-feature/SKILL.md) prepends a synthetic
   invocation header to the sub-agent prompt, of the EXACT form:

       /spec-<subcmd>

   where `<subcmd>` ∈ {`specify`, `plan`, `implement`, `test`, …}. This
   single line is the FIRST line of the sub-agent's user turn, so the
   sub-agent applies steps (1)–(4) of this directive against `<subcmd>`,
   not `feature`. The same rule applies to [`../.agent-sync/skills/spec-ship/SKILL.md`](../.agent-sync/skills/spec-ship/SKILL.md) (batch
   wrapper).
3. Each sub-agent therefore runs (with `--feature <slug>` included when feature
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

## Validation timeout recovery

<!-- @spec FR-007: Bounded evidence-first retry — .specs/features/095-test-time-budgets/spec.md#fr-007 -->
For test/validation scopes, this rule takes precedence over generic retry counts: stop on timeout, retain diagnostics and report scope, effective limit, elapsed duration and enforcement granularity. Never relaunch an identical attempt or increase a timeout merely because it failed. At most one retry requires a documented changed cause or new evidence; initial attempt and retry share 300 seconds, or a prior explicitly declared command maximum up to 600 seconds. Exhaustion leaves validation unresolved and forbids a success claim. Read [validation budgets](testing/execution-rules.md#validation-budgets); this agent policy does not persistently intercept unrelated shell invocations.

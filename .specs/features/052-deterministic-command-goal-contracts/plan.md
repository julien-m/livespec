---
title: "Deterministic Command Goal Contracts Plan"
feature: "052-deterministic-command-goal-contracts"
spec_ref: ".specs/features/052-deterministic-command-goal-contracts/spec.md"
status: Approved
created: 2026-05-21
updated: 2026-05-23
---

# Plan — Feature 052 — Deterministic Command Goal Contracts

- **Feature:** `052-deterministic-command-goal-contracts`
- **Spec:** [spec.md](spec.md)
- **Status:** Approved
- **Date:** 2026-05-21

## Summary

Add a deterministic goal-contract compiler and `livespec goal` CLI that reuse Feature 039 expectations, embed applicable convention domains, then wire the shared anti-drift command protocol to render the goal at startup and verify it before success.

## Technical Context

| Area | Choice |
|------|--------|
| Language | Python 3.11+ |
| CLI | Typer, registered from `validator/cli.py` |
| Existing contract source | `.agent-sync/skills/<command>/expectations.md` via `validator.expectations.load_expectations()` |
| Convention source | `.conventions/index.md` routing to `$AIRESOURCES` source files |
| Existing completion evaluator | `validator.verify_output.evaluate()` |
| Tests | pytest |
| No UI | Visual gates not applicable |

## Constitution Check

| Principle | Verdict |
|-----------|---------|
| Spec as source of truth | OK — this feature adds spec, plan, implementation map, and tests. |
| File-system source of truth | OK — goals compile from versioned files and run artifacts. |
| Deterministic validation | OK — canonical JSON and SHA-256 are deterministic. |
| Local-first execution | OK — no network or external service. |
| Backward compatibility | OK — existing RunArtifact fields remain optional-compatible. |

## Implementation Plan

```mermaid
sequenceDiagram
    participant Cmd as Slash Command
    participant Goal as livespec goal
    participant Exp as expectations.md
    participant Run as RunArtifact
    Cmd->>Goal: render(command, feature, flags)
    Goal->>Exp: load expectations + DoD
    Goal->>Goal: load conventions + select domains
    Goal-->>Cmd: canonical JSON + hash + objective
    Cmd->>Run: record/finalize execution
    Cmd->>Goal: verify(command, feature, flags, run)
    Goal->>Exp: evaluate verify rules
    Goal-->>Cmd: success | drift | error | blocked
```

### Step 1 — Goal compiler module

Create `validator/goal_contracts.py` with:

- `GoalContract`
- `GoalVerification`
- `compile_command_goal()`
- `normalize_goal_flags()`
- `render_goal_objective()`
- `verify_command_goal()`

The compiler loads expectations, extracts DoD lines from `SKILL.md`, canonicalizes verify rules, serializes with sorted JSON, and hashes with SHA-256.

### Step 1.5 — Convention payload compiler

Extend `validator/goal_contracts.py` to:

- Read `.conventions/index.md` when present
- Parse domain names, keywords, `→ $AIRESOURCES/...` source references, and the `$AIRESOURCES` root
- Build a deterministic signal from command, normalized flags, expectations prose, and feature `spec.md`/`plan.md`
- Select `code` by default when present
- Select `design-*` domains when UI/mockup/visual/CSS/screen/theme/baseline/Penflow signals are present
- Embed source path, content, and SHA-256 digest for every selected convention source file

### Step 2 — CLI surface

Create `validator/cli_commands/goal_cmd.py` and register it from `validator/cli.py` as:

- `livespec goal render <command> [--feature X] [--flags "..."] [--json] [--save]`
- `livespec goal prove --contract <contract-file> --state <state-file> --task <task-id> --evidence '<json>'`
- `livespec goal status --state <state-file>`

### Step 3 — Shared command protocol

Update [system/anti-drift-block.md](../../../system/anti-drift-block.md) to require:

- startup goal render + `/goal hash:<hash> ... contract-file:... state-file:...` slash command
- active goal check at start (block if goal already active — user must `/goal clear`)
- per-task `livespec goal prove`
- final `livespec goal status`
- Internal Command Invocation `[subagent]` rows resolve current LiveSpec `project_root`, set child `cwd`/working directory to that root, and fall back to `cd <project_root>` + **Read** [`../../../.specs/spec-system.md`](../../../.specs/spec-system.md) before the child slash command when native cwd is unavailable

### Step 3.5 — Internal subagent audit guard

Extend `validator/goal_contracts.py` and `validator/command_audit.py` so `livespec goal render` and `livespec command-audit` reject executable nested `/spec-*` subagent rows missing `project_root`, `cwd`/working directory, or **Read** [`../../../.specs/spec-system.md`](../../../.specs/spec-system.md).

### Step 4 — Documentation and mappings

Update [system/expectations.md](../../../system/expectations.md), create `implementation.md`, `progress.md`, and changelog entries.

## Testing Strategy

- Unit tests in `tests/test_goal_contracts.py`
- CLI tests in `tests/test_goal_contracts.py`
- Convention selection tests covering code-only and UI/mockup goals
- Audit regression in `tests/test_command_audit_cli.py` for a `[subagent]` row without `project_root`/cwd guard
- Run targeted tests:
  - `python3 -m pytest tests/test_goal_contracts.py tests/test_visual_evidence.py tests/test_visual_gate_receipts.py`
  - `python3 -m pytest tests/test_expectations.py tests/test_verify_output.py tests/test_verify_output_cli.py`

## Risks & Considerations

- `/goal <objective>` is a Claude Code slash command, not a Python CLI API. The CLI renders and verifies goal contracts; the SKILL.md protocol instructs the executor to emit `/goal` at start and check for an already-active goal.
- Definition of Done extraction is Markdown-based. It is intentionally conservative: if no DoD section exists, the compiler returns an empty list instead of inventing conditions.
- The first implementation gates command success through expectations verification. Richer DoD machine evaluation can be added later as a compatible extension.

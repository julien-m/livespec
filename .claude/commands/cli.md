---
description: "Interactive picker for the unified livespec CLI surface (test/coverage/drivers/mutation/preflight)"
argument-hint: "[subcommand] [extra flags]"
---

# Command: /cli

> Interactive entry point for the unified `livespec` CLI surface (Feature 035). Loads the canonical CLI reference, helps you pick the right subcommand, and runs it with the right flags.

The full reference is **Read** [`docs/cli-reference.md`](../../docs/cli-reference.md). Read it before answering any user question about command flags or exit codes — do not infer.

---

## Subcommand index

| Subcommand | Purpose | Key flags | Exit codes specific to it |
|------------|---------|-----------|---------------------------|
| `livespec test` | Run the active driver's coverage capability. | `--feature`, `--mutation`, `--no-coverage` | 0 / 1 / 2 / 3 / 4 |
| `livespec coverage` | Patch coverage vs base branch. | `--base`, `--threshold`, `--report-path` | 0 / 1 / 2 / 3 |
| `livespec drivers` | List all drivers (built-in + custom). | `--json` | 0 / 1 |
| `livespec mutation` | Mutation testing through the active driver. | `--threshold`, `--report-path` | 0 / 1 / 2 / 3 / 4 |
| `livespec preflight` | Verify (or `--fix`) the preflight manifest. | `--fix`, `--full` | 0 / 1 / 5 |

Shared flag on every command: `--debug` (print the full Python stacktrace on errors).

---

## Workflow

1. **If the user provided arguments** (e.g. `/cli test --mutation`):
   - Forward verbatim: run `livespec <args>` from the project root.
   - Surface the structured `LIVESPEC <subcommand> · ...` summary line and the exit code in your answer.

2. **If the user invoked `/cli` with no arguments**:
   - Ask **one** question: "Which subcommand do you want to run? (test / coverage / drivers / mutation / preflight)".
   - Once the user picks, ask **at most one** follow-up about flags only when the choice is ambiguous (e.g. `coverage` without a known base branch). Otherwise run with defaults.

3. **Always**:
   - Run from the repository root (the directory containing `.specs/`).
   - Display the structured summary line at the end of your answer so the user can grep CI logs in the same shape.
   - On non-zero exit, look up the meaning in [`docs/cli-reference.md`](../../docs/cli-reference.md) and propose the next step (e.g. exit 5 → "run `livespec preflight --fix`").

---

## Auto-detection cheat-sheet

The CLI auto-resolves these without flags — only override when something is wrong:

- **Project root** — first ancestor of `cwd` containing `.specs/`.
- **Driver** — `DriverRegistry.discover()` + `pick_primary_driver()`.
- **Base branch** — first hit in: `origin/main`, `origin/master`, `develop`, `dev`, `main`, `master`.
- **Threshold** — `coverage threshold: NN` from `.conventions/index.md`, fallback 70.

---

## Examples to mirror

```
/cli test                         → livespec test
/cli coverage --base develop      → livespec coverage --base develop
/cli drivers --json | jq          → livespec drivers --json | jq
/cli mutation --threshold 75      → livespec mutation --threshold 75
/cli preflight --fix              → livespec preflight --fix
```

---

## Out of scope

- Watch mode / continuous test runner.
- IDE / LSP integration.
- Network reporting (Codecov, Slack notifications) — local-only.
- TUI prompts beyond the single follow-up described above.

For deeper workflows (AC coverage audit, baseline regeneration, design fidelity), use `/spec-test`. For manifest authoring, use `/spec-preflight --regenerate`.

# Test Protocol

> Centralized testing rules for LiveSpec — stack-agnostic, zero hardcoded commands.
> Referenced by `/spec.implement`, `/spec.plan`, and `/spec.check`.

---

## Modules

| File | What it covers | When to read |
|---|---|---|
| [`discovery.md`](discovery.md) | Detect ecosystem, test runners, visual tools, verify & record | `/spec.init` Phase B, `/spec.plan` Step 7.5, first `/spec.implement` if not yet resolved |
| [`execution-rules.md`](execution-rules.md) | When to run tests + final validation checklist | Every `/spec.implement` phase 3, 4, 6 |
| [`failure-handling.md`](failure-handling.md) | Iteration limits, troubleshooting, error reporting format | On test failure during `/spec.implement` |
| [`visual-baselines.md`](visual-baselines.md) | Screenshot capture, comparison, thresholds, archival | UI features only (skip with `--no-visual`) |

All commands come from the **Resolved Test Commands** table in `plan.md` or `.specs/testing/strategy.md`. Never hardcode commands.

---

*LiveSpec Test Protocol v1.1*

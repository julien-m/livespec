# Test Failure Handling

> Iteration limits, troubleshooting procedure, and error reporting format.
> Referenced by `/spec.implement` when tests fail.

---

## Iteration Limits

| Test type | Max iterations | If limit reached |
|---|---|---|
| Unit tests | 3 | Stop, report with context, ask human |
| Integration tests | 3 | Stop, report with context, ask human |
| E2E tests | 5 | Stop, report with diffs, ask human |
| Visual tests | 5 | Stop, report diff images, ask human |
| Static analysis (lint/types) | 3 | Stop, show errors, ask human |

## On Test Failure

1. Read the error message carefully
2. Check if the spec/AC covers this case
3. Fix the issue and re-test
4. If iteration limit reached → use the error reporting format below

## Error Reporting Format

When max iterations are exceeded, report using this structure:

> **Max iterations reached for [test type]**
>
> **Feature:** NNN-feature-name
> **Step:** [current phase/step]
> **Test:** `[test file:line]`
>
> **Failing test:** `"[test description]"`
>
> **Error:**
> ```
> [exact error output]
> ```
>
> **What I tried:**
> 1. Iteration 1: [description]
> 2. Iteration 2: [description]
> 3. Iteration N: [description]
>
> **Likely cause:** [analysis]
>
> **Suggested fix:** [actionable suggestion]
>
> **Action needed:** Please review and fix, then run `/spec.implement [feature] --resume`

---

*LiveSpec Test Protocol — Failure Handling v1.1*

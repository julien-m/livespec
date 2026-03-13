# Test Execution Rules

> When to run tests and final validation checklist.
> Referenced by `/spec.implement` phases 3, 4, and 6.

---

## When to Test

Stack-agnostic rules — applies to all ecosystems:

- **After each implementation step:** run tests targeting the layer just implemented
- **Transverse checks:** lint + type checker on touched files after each step
- **Before declaring a step Done:** the Step Gate in `implement.md` requires tests to pass
- **Before declaring the feature complete:** full suite (unit + integration + E2E if applicable)

All commands come from the **Resolved Test Commands** table. Never hardcode commands.

## Final Validation

Before declaring implementation complete, execute in order:

1. Type checker (if applicable)
2. Linter
3. Full test suite (unit + integration)
4. E2E suite (if applicable)
5. Visual tests (if applicable and tool available)

All commands come from `plan.md` **Resolved Test Commands**. No hardcoded commands.

---

*LiveSpec Test Protocol — Execution Rules v1.1*

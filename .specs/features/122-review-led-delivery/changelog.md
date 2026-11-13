# Changelog

## 2026-11-13 — Feature: Review Led Delivery

- **Type:** Feature
- **Spec modified:** Yes — new feature, workflow, acceptance and migration scope.
- **Code modified:** Read [the diagnostic source selector](../../../validator/goal_payload.py), [command audit](../../../validator/command_audit.py), [shared policy](../../../system/review-led-delivery.md) and [implementation inventory](implementation.md).
- **AC impacted:** AC-001, AC-002, AC-003, AC-004, AC-005, AC-006.
- **Author:** Codex, following explicit user instructions; manually implemented outside LiveSpec execution.

- **Delivery verified:** Public PR56 merged with green code CI; installed compatible LiveSpec/Penflow pair verified, actual consumer runtime and20skills checked. Atlas confirmed its checkpoint, reloaded and resumed a real product correction without certificate prerequisites. Product A1 rendered/native validation remains separate.

## 2026-11-13 — Bootstrap follow-up

Retain concise initialization/migration entry points and operational safeguards from the old isolated work. Remove validation-specific refusal wording; preserve applicable actual refusals. Exclude all new supervisor state and host restart work. Validation and independent correction review are recorded with the follow-up commit.

- **Validation:** 49 targeted checks passed; changed Python Ruff/format checks passed; all current bootstrap reference links resolve; original public archives are byte-exact. Same independent reviewer accepted both targeted corrections with no remaining material finding. No Atlas runtime or service changed.

- **CI follow-up:** first public unit run reported3 failures/4365passes/152skips: routing expected the old inline command list, and the citation scanner omitted extracted operational references. Audit now follows the explicit canonical catalogue link; the scanner includes the current operational references. Unknown-command assertions and citation threshold are unchanged.63 targeted checks pass, including missing-link/target rejection; same reviewer favorable.

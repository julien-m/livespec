# Changelog - 088-capped-reviews

## 2026-10-13 — [Feature]: Capped spec and plan reviews on blockers only

- **Type:** Feature
- **Spec modified:** Yes (created: two stories, four AC, five FR, two SC)
- **Code modified:** validator/semantic/review_contract.py, validator/semantic/review_readiness.py, validator/semantic/review_rounds.py, validator/semantic/acceptance_review.py, validator/cli_commands/review_io.py, validator/semantic_analysis.py, validator/execution_mapping.py, validator/clarify_gate.py, system/review-protocol.md, spec-specify and spec-plan skills, clarify tests
- **AC impacted:** AC-001 through AC-004
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md): a spec or plan review is ready once no blocker remains, `carry_over` lists warnings, non-critical ambiguities and justified technical scope for the next phase, ingestion reports `round` and `round_cap_reached` (third blocked round), and an isolated qualitative word is never a critical clarification. Documentary acceptance and mapping reviews keep requiring `covered`.

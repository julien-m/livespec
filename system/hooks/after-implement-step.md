---
mode: extend
---
<!-- @spec FR-009: Native quality review instructions — .specs/features/050-agent-sync-migration/spec.md#fr-009 -->
<!-- @spec FR-008: No review per step — .specs/features/086-risk-proportional-delivery/spec.md#fr-008 -->

# After Implement Step — checks only, review once at the end

- After a step: run its targeted tests, lint and format of the touched files, and `livespec conventions verify --json --feature <slug>`. A failing check keeps the step Blocked.
- Dispatch no reviewer and no audit for a step. The single review of the complete feature diff uses an independent read-only native agent with reasoning effort `high` at the end of the feature, as defined in the [delivery review protocol](../delivery-review.md); its lane (one `combined` reviewer, or a `review` plus an `audit` reviewer) is decided by `livespec delivery lane`.
- Never invoke the retired audit skill, Codex, a Python audit launcher or cc-hub. A historical global copy of this hook that requires a per-step review or the audit skill is replaced as described in `system/hooks.md` (Native quality review).

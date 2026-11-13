---
name: spec-feature
description: "Deliver a feature through implementation and one independent final review."
---
<!-- @spec FR-001: Review led delivery — .specs/features/122-review-led-delivery/spec.md#fr-001 -->


# spec-feature

Read [review led delivery](../../../system/review-led-delivery.md) before acting. Resolve this link from this skill's real directory when installed through symlinks. This is the default for direct, nested, autonomous and resumed work; no extra flag selects it.

Treat [the former certification workflow](certification.md) as an explicit historical diagnostic only. Do not load or execute it during normal delivery. Historical CLI checks keep their real verdicts and never become automatic delivery prerequisites.

## Work

1. Read the requested feature, project context and applicable conventions. Reuse existing spec, plan, decisions and implemented code on resume; do not restart completed work.
2. Write or update only the brief spec and plan needed for this change. Reuse any existing plan review; do not add an automatic review before implementation. Ask only for an unresolved functional choice.
3. Implement the feature and run useful scoped checks. Continue to review when a script fails or is unavailable, carrying its actual output and impact.
4. Dispatch one fresh native final reviewer under the shared policy. Correct concrete findings and recheck the affected behavior; do not restart the pipeline.
5. Update implementation mappings, changelog and status from the final review and actual observations. Report remaining limits. Commit, publish or deploy only within the user's authorization.

Apply these steps directly; do not spawn a separate goal-bearing command agent for every phase. A specialized worker may own a bounded implementation task when delegation is authorized, but uses the same nonblocking check policy.

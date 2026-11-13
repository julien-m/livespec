---
name: spec-plan
description: "Prepare a short implementation plan for the requested change."
---
<!-- @spec FR-001: Review led delivery — .specs/features/122-review-led-delivery/spec.md#fr-001 -->


# spec-plan

Read [review led delivery](../../../system/review-led-delivery.md) before acting. Resolve this link from this skill's real directory when installed through symlinks. This is the default for direct, nested, autonomous and resumed work; no extra flag selects it.

Treat [the former certification workflow](certification.md) as an explicit historical diagnostic only. Do not load or execute it during normal delivery. Historical CLI checks keep their real verdicts and never become automatic delivery prerequisites.

## Work

1. Resolve the feature and read its spec, decisions, project constraints and applicable conventions before planning.
2. Describe the modules/contracts that change, the intended behavior and the useful checks. Keep the plan proportional; do not add a certification pipeline or a mechanism without a product need.
3. Resolve material contradictions and missing functional choices. Reuse an existing plan review; dispatch a separate plan review only when the user asks for it. No JSON ingestion, reviewer identity gate, review receipt or continuity protocol is required.
4. Save the plan and any available review conclusions. Return them to the parent without extra phase agents or goals.

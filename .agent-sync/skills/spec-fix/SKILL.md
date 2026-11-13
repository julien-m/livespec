---
name: spec-fix
description: "Fix a reported product gap without restarting feature certification."
---
<!-- @spec FR-001: Review led delivery — .specs/features/122-review-led-delivery/spec.md#fr-001 -->


# spec-fix

Read [review led delivery](../../../system/review-led-delivery.md) before acting. Resolve this link from this skill's real directory when installed through symlinks. This is the default for direct, nested, autonomous and resumed work; no extra flag selects it.

Treat [the former certification workflow](certification.md) as an explicit historical diagnostic only. Do not load or execute it during normal delivery. Historical CLI checks keep their real verdicts and never become automatic delivery prerequisites.

## Work

1. Resolve the reported issue and existing feature. Read the relevant requirements, code, decisions and conventions. A missing gap report or stale receipt does not prevent diagnosis.
2. Reproduce when useful, fix the cause and run checks relevant to the correction. Preserve actual failures and unavailable observations for review; do not render or prove a goal.
3. Obtain the shared independent final review for the complete correction, or return results to the parent that owns that review. Fix material findings without a full feature revalidation loop.
4. Update affected mappings and changelog. Preserve unrelated requirements and existing evidence.

Honor `--dry-run` and `--audit-only` as read-only. `--visual`, `--fr` and `--ac` scope the correction; `--bugfix` no longer creates a separate RED/GREEN certification lane. `--conventions` fixes relevant convention issues without a debt-decreasing gate.

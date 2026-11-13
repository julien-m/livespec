---
name: spec-test
description: "Run useful product checks and report their results for review."
---
<!-- @spec FR-001: Review led delivery — .specs/features/122-review-led-delivery/spec.md#fr-001 -->


# spec-test

Read [review led delivery](../../../system/review-led-delivery.md) before acting. Resolve this link from this skill's real directory when installed through symlinks. This is the default for direct, nested, autonomous and resumed work; no extra flag selects it.

Treat [the former certification workflow](certification.md) as an explicit historical diagnostic only. Do not load or execute it during normal delivery. Historical CLI checks keep their real verdicts and never become automatic delivery prerequisites.

## Work

1. Resolve the feature and read its expected behavior, changed paths and existing test commands. Respect audit-only, no-generation and read-only requests.
2. Select the smallest meaningful set of tests, build, type, lint and runtime checks for the change. Add a missing regression only when it proves a concrete behavior or risk; no exhaustive generated matrix.
3. Execute the selected checks, retaining commands, exit codes, failures and unavailable checks. Reuse results whose relevant inputs have not changed.
4. Send findings to the owning final review. A nonzero command is a finding, not an automatic BLOCKED phase. Do not certify, generate runner manifests, run nested goals or require formal Penflow/visual receipts.
5. If invoked alone, report what passed, failed and remains unknown; do not silently repair sources or approve delivery.

For UI changes, inspect actual runtime rendering against the relevant design when the necessary tools are available. Missing native observations remain missing; never substitute a static assertion or code reading for an interaction.

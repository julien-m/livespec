---
name: spec-migrate
description: Apply a LiveSpec project's planned format migrations while preserving restore points, runtime identity and history; report real outcomes and explicit rollback limits.
---
<!-- @spec FR-003, FR-004: Bootstrap migration — .specs/features/122-review-led-delivery/spec.md#fr-003 -->

# spec-migrate

Read [review led delivery](../../../system/review-led-delivery.md) first, resolving this link from the skill's physical directory through installed symlinks. It governs direct, nested, autonomous and resumed migrations. No nested goal, semantic receipt, separate plan review or certification helper is required.

## Plan before mutation

1. Resolve the existing `.specs/`, project version and effective LiveSpec source. On a pinned project, use the snapshot already selected by the authorized runtime upgrade, never another checkout or mutable `current`. Verify VERSION and required migration scripts; do not downgrade a newer project implicitly.
2. Read [the migration procedure](migration.md#execution-flow) and run `livespec migrate plan --project <project> --livespec <resolved-source> --json`. Respect its ordered `apply`, supersession metadata and unsafe restore-point warnings; never infer success from version numbers alone.
3. `--dry-run` and other read-only requests inspect the plan only: no path/version writes, sync, hooks, restore-point creation, scaffolding or inverse. `--force` requests a compatible historical replay; inspect its real actions as described in the technical reference, without inventing a planner flag. It never discards a restore point or permits an unbacked overwrite. Resolve real functional choices or missing authority before dependent writes.

## Apply and observe

- Execute only planned migrations in order with `bash <source>/scripts/migrate.sh <source>/migrations/N/migrate.md <project> <source>`. Preserve the first complete pre-image, modes, links and history. Never replace an existing restore point on retry.
- A missing/invalid planned migration, nonzero executor result or altered restore point is a concrete integrity problem. Retain its exact result and leave dependent actions unapplied; do not bump the version, re-pin or announce completion to hide it. Continue independent diagnosis/review without a certification restart.
- Check actual versions, managed links, effective runtime and retained project content after execution. Keep unknown observations `NOT_RUN` and distinguish a failed migration from an unrelated administrative finding.
- Visual scaffolding/reconciliation/E2E generation are optional follow-up, only when requested. Read [those technical details](migration.md#optional-visual-follow-up) for that scope; preserve real existing tests and report unavailable UI observations honestly.
- Rollback is a separate explicit user action. Read [the shipped inverse procedure](migration.md#rollback), use the newer snapshot's inverses in reverse order and re-pin only after successful restoration. Never delete backups/journals or alter restore-point metadata to bypass refusal.
- Return migration results and relevant checks to the parent owning the shared final review, or obtain that review under the shared policy. Correct material migration defects and report remaining limits; no independent feature or plan review is launched as a prerequisite.

Read [the former certification workflow](certification.md) only for an explicitly requested historical diagnostic. Historical inventories, results and active mission records are not rewritten by this policy.

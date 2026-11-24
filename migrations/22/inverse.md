---
version: 22
name: conventions-migration-docs-inverse
description: "Inverse of migration 22: restore the scope recorded before it ran"
date: 2026-11-11
kind: asset-sync
---

# Inverse of Migration v22

<!-- @spec FR-004: Restore the recorded migration scope
     — ../../.specs/features/122-review-led-delivery/spec.md#fr-004 -->

Restores the restore point that migration 22 recorded in
`.specs/.migration-restore/22/` before its first generator ran: every recorded
path gets back its bytes, mode or symlink target, the paths the migration
created inside the recorded scope are removed, the project version file holds
its value from before the migration again, and the restore point is deleted.

Run it after the inverse of migration 23, with the same executor:
`scripts/migrate.sh migrations/22/inverse.md <project> <livespec>`. It refuses,
changing nothing, when no restore point exists, when a recorded pre-image is
missing or altered, or when the project version is above 22. The migration
planner loads only `migrate.md`, so this file runs only when invoked explicitly.

RUN migrate-restore-point.py restore 22

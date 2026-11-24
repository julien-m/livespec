---
version: 23
name: technical-recovery-stop-rules
description: "Record the format-23 recovery policy without adding delivery prerequisites"
date: 2026-11-24
kind: asset-sync
---

# Migration v23

<!-- @spec FR-004: Apply format 23 with the explicit recovery-policy marker
     — ../../.specs/features/122-review-led-delivery/spec.md#fr-004 -->

The migration creates the schema-1 recovery policy expected by format 23 and
preserves an existing project policy. This marker is for explicit recovery
tools. Standard skills continue to use [review-led delivery](../../system/review-led-delivery.md).

The migration records its pre-images before applying the new format. Read
[inverse.md](inverse.md) for the rollback procedure.

RUN migrate-restore-point.py record 23 .gitignore .specs/livespec-version .specs/recovery-policy.yaml
GITIGNORE /.specs/.migration-restore/
RUN migrate-recovery-policy.sh
SET_VERSION 23

---
version: 23
name: technical-recovery-stop-rules-inverse
description: "Restore the format-22 version and policy pre-images"
date: 2026-11-24
kind: asset-sync
---

# Inverse of Migration v23

<!-- @spec FR-004: Restore the format-22 version and recovery policy
     — ../../.specs/features/122-review-led-delivery/spec.md#fr-004 -->

Apply this inverse before the [migration 22 inverse](../22/inverse.md). It
restores the recorded version, policy and ignore file. When an earlier snapshot
migrated a project without recording this restore point, use that snapshot's
original inverse for migration 23.

RUN migrate-restore-point.py restore 23

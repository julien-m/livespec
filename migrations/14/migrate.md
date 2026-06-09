---
version: 14
description: "Command validation hardening — audit-backed command surface and local coverage artifacts"
date: 2026-05-18
---
<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-012) -->


# Migration v14: Command Validation Hardening

Feature 048 adds the deterministic `livespec command-audit` gate, command
run finalization, and local `play-coverage` data generation. Downstream
projects should refresh local command symlinks and ignore generated coverage
playground data.

## Actions

RUN migrate-command-validation.sh
GITIGNORE playground/coverage/
SET_VERSION 14

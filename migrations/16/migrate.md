---
version: 16
name: agent-sync-migration
description: Synchronize LiveSpec skills, agents, and rules through cc-hub
---

GITIGNORE .agent-sync.local/
RUN migrate-agent-sync.sh
SET_VERSION 16

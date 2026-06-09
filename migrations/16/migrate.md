---
version: 16
name: agent-sync-migration
description: Synchronize LiveSpec skills, agents, and rules through cc-hub
---
<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-006) -->


GITIGNORE .agents/skills/spec-*
GITIGNORE .claude/skills/spec-*
GITIGNORE .claude/rules/*.md
GITIGNORE .claude/rules/livespec/
GITIGNORE .codex/agents/livespec-*.toml
RUN migrate-agent-sync.sh
SET_VERSION 16

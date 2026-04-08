---
version: 2
description: "Transition from global to local command distribution"
date: 2026-04-08
---

# Migration v2: Local Command Distribution

Moves all spec.* commands and livespec-* agents from global ~/.claude/
to project-local .claude/ directories via symlinks.

## Actions

MKDIR .claude/commands
MKDIR .claude/agents
RUN link-local.sh
GITIGNORE .claude/commands/spec.*.md
GITIGNORE .claude/agents/livespec-*.md
GITIGNORE .specs/.livespec-path
SET_VERSION 2

---
name: link
description: Link all LiveSpec commands and agents globally (spec.<name> + livespec-<name>)
model: haiku
allowed-tools: Bash(cc-hub :*), Bash(ls :*), Bash(ln :*), Bash(readlink :*), Read, Glob
---

# Link all LiveSpec commands and agents

Synchronize all commands and agents from the project to their global Claude Code locations.

## Context

- Commands directory: !`ls commands/`
- Agents directory: !`ls agents/`
- Currently linked commands: !`cc-hub command list 2>&1 | grep spec || echo "None"`
- Currently linked agents: !`ls -la ~/.claude/agents/ 2>&1 | grep livespec || echo "None"`

## Workflow

### 1. Link commands

For each `.md` file in `commands/`:

```
cc-hub command link commands/<name>.md --name spec.<name>
```

### 2. Link agents

For each `.md` file in `agents/`:

```
ln -sf "$(pwd)/agents/<filename>" ~/.claude/agents/<filename>
```

### 3. Verify

- Run `cc-hub command list` — confirm all `spec.*` entries
- Run `ls -la ~/.claude/agents/ | grep livespec` — confirm all `livespec-*` symlinks

### 4. Report

Report which commands and agents were linked, skipped, or failed.

## Rules

- Command link names MUST follow `spec.<name>` (e.g. `commands/init.md` → `spec.init`)
- Agent symlink names keep their original filename (e.g. `agents/livespec-supervisor.md` → `~/.claude/agents/livespec-supervisor.md`)
- Link ALL `.md` files found in both directories — no exceptions
- If a link already exists, re-link it (idempotent)
- Do NOT modify any command or agent files — only create links

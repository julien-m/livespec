---
name: link-commands
description: Link all LiveSpec commands globally via cc-hub (spec.<name>)
model: haiku
allowed-tools: Bash(cc-hub :*), Bash(ls :*), Read, Glob
---

# Link all LiveSpec commands

Link every command from the `commands/` directory as a global Claude Code command using `cc-hub command link`, with the naming convention `spec.<command_name>`.

## Context

- Commands directory: !`ls commands/`
- Currently linked: !`cc-hub command list 2>&1 | grep spec || echo "None"`

## Workflow

1. List all `.md` files in the `commands/` directory
2. For each file `<name>.md`, run:
   ```
   cc-hub command link commands/<name>.md --name spec.<name>
   ```
3. After linking all commands, run `cc-hub command list` to verify
4. Report which commands were linked, skipped, or failed

## Rules

- The link name MUST follow the pattern `spec.<name>` (e.g. `commands/init.md` → `spec.init`)
- Link ALL `.md` files found in `commands/` — no exceptions
- If a link already exists, re-link it (idempotent)
- Do NOT modify any command files — only create symlinks via cc-hub

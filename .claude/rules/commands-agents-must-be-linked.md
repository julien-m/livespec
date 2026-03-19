---
name: Commands and Agents Must Be Linked
description: Ensure new commands and agents are globally linked via cc-hub when created
type: feedback
---

# Commands and Agents Must Be Linked

**Rule:** Every new command or agent created in this project MUST be linked globally via `cc-hub` before being considered complete.

**Why:** Commands and agents need to be discoverable and usable from any Claude Code session in this workspace. Without linking, developers won't see them in the global command list and can't invoke them. The link-commands skill automates this, but developers must explicitly run it after creating new files.

**How to apply:**

## When creating a new command:

1. Add the `.md` file to `commands/`
2. After completing the file, run the link-commands skill:
   ```bash
   /link-commands
   ```
3. Verify the command is now in `cc-hub command list | grep spec.your-command-name`
4. Update `README.md` if it contains a commands list

## When creating a new agent:

1. Add the `.md` file to `agents/`
2. Run a similar linking command:
   ```bash
   cc-hub skill link agents/<name>.md --name livespec-<name>
   ```
3. Verify it appears in `cc-hub skill list`
4. Update `README.md` or relevant documentation

## In commit messages:

Include "links: spec.command-name" or "links: livespec-agent-name" when committing new commands/agents to signal that linking is complete:

```
feat: add spec.preflight command

This adds the new preflight verification system.

links: spec.preflight
```


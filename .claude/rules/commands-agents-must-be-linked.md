# Commands and Agents Must Be Linked

**Rule:** Every new command or agent created in this project MUST be linked globally before being considered complete.

**Why:** Commands and agents need to be discoverable and usable from any Claude Code session. Without linking, they won't appear in the global list and can't be invoked.

**How to apply:** After creating or modifying any `.md` file in `commands/` or `agents/`, run the `/link` skill. It handles both commands and agents in a single pass.

```bash
/link
```

Verify with:
- `cc-hub command list | grep spec.` — commands
- `ls -la ~/.claude/agents/ | grep livespec` — agents

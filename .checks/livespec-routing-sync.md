<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-009) -->

# LiveSpec Routing Sync

## When
Staged files match `.agent-sync/skills/spec-*/SKILL.md`,
`.agent-sync/skills/spec-*/expectations.md`, or
`.agent-sync/rules/livespec/commands.md`.

## Verify
The set of command skill directory names in `.agent-sync/skills/` must match
exactly the set of `### /spec-*` headings in
`.agent-sync/rules/livespec/commands.md`. Skill directory names carry the
canonical `spec-` prefix (e.g. `.agent-sync/skills/spec-test/` ↔ heading
`### /spec-test`).

Compare these two lists:

- Skills: `find .agent-sync/skills -mindepth 1 -maxdepth 1 -type d -name 'spec-*' | sed 's|.*/||' | sort`
- Headings: `grep -E '^### /spec-' .agent-sync/rules/livespec/commands.md | sed 's|^### /||' | sort`

The two lists must be identical. Any orphan heading without a corresponding
skill, or any missing heading for a skill, blocks the commit without exception.
The error report must list both diffs explicitly (orphans + missing) so the
human knows exactly what to add or remove.

This check is **blocking, no exceptions** — any new spec skill added to
`.agent-sync/skills/`, or any skill removed, must be reflected in
`livespec-commands.md` in the same commit.

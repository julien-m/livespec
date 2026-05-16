# LiveSpec Routing Sync

## When
Staged files match `commands/*.md` (excluding `*.expectations.md`) or `.claude/rules/livespec-commands.md`.

## Verify
The set of command names in `commands/` must match exactly the set of `### /spec.X` headings in `.claude/rules/livespec-commands.md`. Command filenames in `commands/` do NOT carry the `spec.` prefix (e.g. `commands/test.md` ↔ heading `### /spec.test`).

Compare these two lists:

- Files: `find commands -maxdepth 1 -name '*.md' -not -name '*.expectations.md' | sed 's|.*/||;s|\.md$||' | sort`
- Headings: `grep -E '^### /spec\.' .claude/rules/livespec-commands.md | sed 's|^### /spec\.||' | sort`

The two lists must be identical. Any orphan (heading in `livespec-commands.md` without a corresponding file in `commands/`) or any missing entry (file in `commands/` without a corresponding heading) blocks the commit without exception. The error report must list both diffs explicitly (orphans + missing) so the human knows exactly what to add or remove.

This check is **blocking, no exceptions** — any new spec command added to `commands/`, or any command removed, must be reflected in `livespec-commands.md` in the same commit.

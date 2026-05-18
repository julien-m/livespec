---
version: 13
description: "Backfill command expectations wiring — verify-output symlinks, last_reviewed hook, gitignore (Features 039, 040)"
date: 2026-05-13
---

# Migration v13: Command Expectations Wiring

Features 039 (command expectations + `/spec-verify-output` + last-reviewed
pre-commit hook) and 040 (rich expectations + `--preview` / `--save`) added
runtime artefacts that were not auto-wired into pre-v13 projects:

- **New slash command** `/spec-verify-output` — needs a symlink in
  `.claude/commands/`.
- **Sidecar metadata** `commands/*.expectations.md` — read directly from
  the LiveSpec checkout by `livespec verify-output`. The pre-fix
  `link-local.sh` did not filter these and mistakenly created
  `.claude/commands/spec.<cmd>.expectations.md` entries that polluted the
  Claude slash-command menu.
- **Pre-commit hook** `hooks/livespec-last-reviewed.py` — enforces that
  `last_reviewed` markers in expectations files stay current. Never
  installed automatically before v13.
- **Gitignore entries** `.specs/.runs/` (run-wrapper artefacts) and
  `.specs/.previews/` (`verify-output --preview/--save` output) — both
  are local-only by design.

This migration re-runs the patched `link-local.sh` (which now skips
`*.expectations.md` and removes any orphan symlinks left by the buggy
prior version) and the canonical `install-hooks.sh` (idempotent — keyed
off the `# livespec-expectations` marker). Both gitignore patterns are
also appended via the `GITIGNORE` DSL verb for projects that drive
LiveSpec without invoking `install-hooks.sh` (e.g. no `.git/` directory,
sub-tree layouts).

Projects with no `.claude/commands/` directory (those that rely solely
on the global `/spec.*` commands) skip the link refresh silently.
Projects without `.git/` skip the hook install silently. Re-running the
migration on an already-migrated project is a no-op.

## Actions

RUN migrate-expectations.sh
GITIGNORE .specs/.runs/
GITIGNORE .specs/.previews/
SET_VERSION 13

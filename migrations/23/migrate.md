---
version: 23
name: init-bootstrap-repair
description: "Repair spec-init bootstrap artifacts so they pass livespec validate and the init definition of done"
date: 2026-10-13
kind: asset-sync
---

<!-- @spec FR-006: Migration v23 bootstrap repair
     — ../../.specs/features/080-autonomous-from-code-recovery/spec.md#fr-006 -->

# Migration v23: Init Bootstrap Repair

Feature 080 (FR-005) corrected `/spec-init` so that a fresh bootstrap passes
`livespec validate`, keeps the installer's ignore patterns and command list and
creates the design inventory. This migration brings projects initialized
earlier to the same state, without rewriting user content:

- renames only the initial `## <date> — LiveSpec initialized` changelog heading
  to `## <date> — [Setup]: LiveSpec initialized`;
- adds a `Tokens` section to `preflight.md` when no Tokens/Credentials/Keys
  section exists, before the custom block;
- adds `title: Default Stack` to the `stacks/_default.md` frontmatter;
- creates `.specs/design/screens/index.md` and `.specs/design/changelog.md`
  when absent, and adds the missing ignore patterns;
- replaces a LiveSpec block in `CLAUDE.md`/`AGENTS.md` only when it has no
  `Commands:` line;
- refreshes `.specs/bootstrap-profile.json` for each file it changes, so the
  autonomous `--verify-only` check stays green.

A second run changes nothing. Migration v22 (conventions bootstrap) was never
reachable because VERSION stayed 21; raising VERSION to 23 applies it first,
as the user decided on 2026-10-13.

RUN migrate-init-bootstrap-repair.sh
SET_VERSION 23

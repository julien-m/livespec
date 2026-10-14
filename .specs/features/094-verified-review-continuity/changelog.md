# Changelog - 094-verified-review-continuity

## 2026-10-14 — [Feature]: Stored source roles and revision records verified at their commit

- **Type:** Feature
- **Spec modified:** Yes (created: two stories, three AC, three FR, one SC)
- **Code modified:** validator/semantic/review_context.py, validator/semantic/review_stability.py, validator/delivery/revision.py, validator/delivery/revision_commit.py (new), validator/progression_gate.py, validator/pipeline_review_validation.py, system/review-protocol.md, spec-implement skill
- **AC impacted:** AC-001 through AC-003
- The reviewed context stores the role of every source, so an empty linked document no longer makes a current review stale. `livespec delivery revision open` records the HEAD commit; the `implement` and `test` progressions accept the recorded receipts only while that commit is an ancestor of HEAD and the reviewed sources at it have the same stable identity (`spec_revision_unverified`, `spec_revision_uncommitted`).
- Origin: two warnings carried from the 089 delivery review; the maintainer asked to fix them (14 October 2026).
- Delivery review round 1 (review PASS with warnings, audit BLOCKED) fixed: a hand-written record naming a commit where a new linked document was added passed, because only the reviewed sources were re-read; the commit's tree is now prepared like a real opening. Also: only full object ids are accepted, replace objects are ignored, CRLF checkouts and symlinked sources verify, and line endings no longer change the stable identity of plan and context sources.
- Delivery review round 2 (review and audit BLOCKED) fixed: `git archive` broke projects in a repository subdirectory and applied local smudge filters, which let a hand-written record pass; the commit's tree is now written from raw objects (`ls-tree`, `cat-file --batch`) with literal pathspecs, a configuration differing only in line endings matches, and a symlink loop at the commit is refused without crashing.
- Delivery review round 3 (review BLOCKED, audit PASS with a matching warning) fixed: a crafted tree whose chained symlinks passed the lexical check let the writer create a file outside the temporary directory. Regular blobs are now written first, nothing is written under a symlink and a link resolving physically outside the tree is removed; chained links resolve; the cat-file output is parsed by offset. Refusals for committed `ident`/smudge attributes are documented.
- Delivery review round 4: review PASS, audit PASS. Known limits, all failing closed with `spec_revision_uncommitted`: a source reached through a directory symlink, or a link whose target normalizes to `..`, cannot open a revision; an escaping link is dropped (the record is refused only when that changes the reviewed sources).

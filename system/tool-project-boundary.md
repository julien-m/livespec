<!-- @spec FR-010: Tool/project boundary rule — .specs/features/083-pinned-runtime-isolation/spec.md#fr-010 -->

# Tool/Project Boundary

> Applies to every session whose project is a LiveSpec consumer (any project other than the LiveSpec repository), in **every lock mode** of `.specs/livespec.lock` (pinned, dev or none). Dev mode only changes which runtime executes; it never relaxes these rules.

A **LiveSpec root** is any directory holding `VERSION`, `validator/` and `.agent-sync/`: an installed runtime snapshot under `<home>/versions/<id>/` or a LiveSpec checkout. The root used by the project is recorded in `.specs/.livespec-path`.

## Rules

1. **Never touch a LiveSpec root from a consumer session.** Do not edit, format, commit, push, branch or run lifecycle commands (`/spec-*`, `$spec-*`, `livespec finalize`, `livespec pipeline`, tests) inside any LiveSpec root, whether snapshot or checkout. Read-only inspection is allowed.
2. **Report a blocking tool defect, then block the phase.** When a LiveSpec command fails because of LiveSpec itself (crash, wrong gate, broken skill), record it in the project and stop the phase:
   ```bash
   livespec runtime defect --command '<failing command>' --error '<verbatim error>' \
     --feature <feature-slug> --phase <phase> --title '<short title>'
   ```
   This writes `.specs/tool-defects/<YYYY-MM-DD>-<slug>.md` in the project and marks the phase `Blocked` in `pipeline.md`. Report the defect path to the user; do not work around the defect.
3. **Project closure never depends on a LiveSpec repository lifecycle.** Never launch `/spec-fix`, `/spec-feature` or any other workflow on the LiveSpec repository to unblock a consumer feature, and never make a consumer phase wait on one.
4. **The fix ships in LiveSpec separately; the project resumes after an upgrade.** The LiveSpec fix is made in a session whose project is the LiveSpec repository and installed as a new runtime. The consumer then resumes:
   - pinned: `livespec runtime upgrade --to <fixed runtime>`, then resume the blocked phase;
   - unpinned: `livespec runtime pin --runtime <fixed runtime>`, then resume the blocked phase;
   - dev: update the dev checkout to a commit containing the fix, then resume the blocked phase.

## Why

Consumer projects used to execute the mutable LiveSpec development checkout, so every LiveSpec repair changed the rules of running consumer projects, and a consumer feature once depended on a full LiveSpec `/spec-fix`. Pinned snapshots plus this rule keep tool defects out of the project critical path.

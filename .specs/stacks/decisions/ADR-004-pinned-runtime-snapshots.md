# ADR-004: Pinned Runtime Snapshots, Runtime Command Group and Shim Installation

- **Date:** 2026-10-11
- **Status:** Accepted (feature [083-pinned-runtime-isolation](../../features/083-pinned-runtime-isolation/spec.md), recorded during planning before implementation)
- **Context:** Consumer projects (for example `~/projects/handy`) executed the LiveSpec development checkout directly: `/opt/homebrew/bin/livespec` is an editable install of `~/projects/livespec/validator`, and the projects' `.specs/.livespec-path` plus `.agent-sync.local/{skills,rules}` symlinks point into that checkout. Every uncommitted LiveSpec edit changed the rules of running consumer projects, and a LiveSpec tool defect pulled a LiveSpec repository lifecycle into a consumer feature's critical path. The constitution (principles 3, 5, 6) did not allow writes outside the target project, listed a fixed subcommand set, and named only the editable/bootstrap installation paths.
- **Decision:**
  1. **Write scope:** `livespec runtime install` writes only under a user-selected runtime home (`--home`, else `$LIVESPEC_HOME`, else `~/.livespec`): read-only snapshots in `versions/<VERSION>-<sha12>/`, the `current` pointer and the generated `bin/livespec` shim. This is an explicit, user-invoked machine-local install scope, like `scripts/install.sh`. Project-scoped runtime commands (`pin`, `upgrade`, `dev`, `defect`, `status`) write only inside the target project.
  2. **CLI surface:** one command group `livespec runtime` (`install`, `pin`, `upgrade`, `dev`, `status`, `defect`) following the existing command-group pattern (`pipeline`, `goal`, `hooks`, `finalize`); behaviour is composed with flags (`--home`, `--project`, `--ref`, `--no-activate`, `--json`). The group bypasses the migration guard so recovery works on stale projects.
  3. **Installation model:** immutable snapshots built only from committed git trees plus a standalone shim are added beside the editable install, which stays unchanged. Projects pin a runtime in a committed `.specs/livespec.lock`; the shim resolves pinned snapshot → declared dev checkout → `<home>/current`.
- **Alternatives considered:**
  - **Publish to PyPI / `uv tool install`** — rejected for this feature: requires network and a release process; out of scope per spec.
  - **Per-project vendored copies** — rejected: duplicates the runtime per project and still needs a shim to select it.
  - **Refuse execution of the editable CLI** — rejected: detection only (`runtime status` / `doctor` ERROR); refusal is out of scope.
  - **`git archive` for snapshot export** — rejected: applies `export-ignore`/`export-subst` attributes; snapshots use `git ls-tree` + `git cat-file --batch` for exact committed bytes.
- **Consequences:**
  - Constitution principles 3, 5 and 6 are amended in the same change to reference this ADR (the constitution takes precedence over ADRs).
  - Snapshots carry LiveSpec sources only; third-party dependencies come from the interpreter that ran `runtime install`, recorded in the shim.
  - Snapshots are read-only; no deletion command is provided — documentation explains restoring write permission before manual deletion.
  - Consumer projects commit `.specs/livespec.lock`; `.specs/.livespec-path` and `.agent-sync.local/` stay machine-local and are re-materialized by `livespec runtime pin --runtime <locked id>` after the snapshot's own `scripts/link-local.sh`.

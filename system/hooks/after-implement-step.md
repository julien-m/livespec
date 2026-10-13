---
mode: extend
---
<!-- @spec FR-009: Native quality review instructions — .specs/features/050-agent-sync-migration/spec.md#fr-009 -->

# Native Quality Review — After Implement Step and Before Commit

- After a step: run only after its tests, Spec Reviewer and Code Quality Reviewer pass; review the step's complete change set. A Blocked step stays Blocked.
- Before finalization/commit: review the complete authorized feature or fix diff, including unstaged and untracked source/test files. A step-only PASS never certifies the full diff.
- Use an independent read-only native agent with reasoning effort `high`, the caller's resolved model, and its explicit review budget when present. Do not invoke the retired audit skill, a Python audit launcher or cc-hub for this review. If native dispatch or `high` is unavailable, report BLOCKED; do not silently skip or lower effort.

Native review wait: `timeout=300s`; wait in slices of at most 60s so progress remains observable. Timeout keeps the run BLOCKED.

## Inputs and Scope

1. Resolve the target repository, feature/step, base revision and exact files. Capture the diff and SHA-256 identities of the reviewed file bytes (including untracked files) before dispatch; record deletions explicitly. Never stage, unstage, reset, commit or push for review. Preserve the user's index.
2. Read repository AGENTS.md, CLAUDE.md and applicable rules, the feature spec/plan/implementation, and `.conventions/index.md`. Resolve and read each selected convention source with its exclusions; pass the loaded content to the reviewer. Missing required conventions blocks review.
3. Read applicable user checks in `~/.claude/checks/`, `~/.codex/checks/`, project `.checks/` and `.claude/checks/`, including their scope predicates. Checks outside the reviewed diff need no execution. Run required checks through the authorized implementing agent and provide real command, exit and output evidence to the reviewer. Missing evidence never counts as PASS.
4. Give the reviewer the complete scope, diff, identities, conventions and check evidence. If the context budget is too small, split explicit domains into independent native `high` agents and aggregate every report; record coverage. Never truncate silently or accept unreviewed files.

## Verdict and Corrections

- The reviewer modifies no files and returns PASS or BLOCKED plus findings: file/line, severity, applicable rule or requirement, evidence and proposed correction. Explain false positives with evidence. Preserve nonblocking findings separately.
- Save the actual returned report under the feature's `checks/` (or `.specs/checks/` for a repository fix), with agent identity, model, effort, base, file hashes, reviewed scope, commands/exits, findings and verdict. Record its path in the progress checkpoint/commit context; do not invent a LiveSpec review receipt from prose.
- PASS requires complete scope, successful required checks, zero unresolved blocking findings and file identities unchanged since dispatch. Recheck identities before advancing; a change invalidates PASS.
- On BLOCKED, the authorized implementing agent may apply scoped fixes, rerun affected checks and dispatch a fresh independent native `high` review of the complete changed scope. At most two correction iterations; record each report and corrected findings.
- Remaining blocking findings, failed checks, missing report, timeout, dispatch failure or incomplete coverage keep the step/finalization BLOCKED. Do not downgrade findings to warnings or continue to the next step/commit after exhausting retries.
- Existing Spec/Plan/Code Quality, conventions, execution and acceptance gates remain required. This quality report is independent evidence; it cannot certify those gates, runtime behavior or feature completion.

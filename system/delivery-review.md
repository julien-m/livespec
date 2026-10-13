<!-- @spec FR-008: End-of-feature delivery review protocol — .specs/features/086-risk-proportional-delivery/spec.md#fr-008 -->

# Delivery Review — once per feature, on the complete diff

Implementation steps run only targeted tests, lint, format and the conventions gate. Spec compliance, code quality and audit are reviewed **once**, at the end of the feature, on the complete diff. The lane decides how many independent reviewers run; the CLI decides the lane (`livespec delivery lane --feature <slug> --model <m>`), never the agent.

| Lane | When (CLI-verified) | End-of-feature reviewers |
|---|---|---|
| light | Low or Medium criticality, Local or Shared blast radius, no `**Delivery lane:** full`, current ready spec review | one `combined` report: spec compliance, code quality and audit |
| full | every other case, including a missing or conflicting QE classification | one `review` report (spec compliance, code quality) and one `audit` report (security, robustness, conventions), from two independent agents |

## Procedure

1. **Scope.** `livespec delivery review prepare --feature <slug> --base <rev> --model <m> --json`, where `<rev>` is the revision the feature started from: the commit before the one that created `.specs/features/<slug>/spec.md` (`git log --diff-filter=A --format=%H -- .specs/features/<slug>/spec.md | tail -1`, then its parent), or an older ancestor of HEAD; a newer base is refused with `base_not_feature_start`. A spec or plan change limited to lifecycle metadata (status, dates) is not part of the scope. It hashes every path of the diff (tracked, staged or not, and untracked non-ignored files), except LiveSpec traceability files (`implementation.md`, changelogs, `progress.md`, `pipeline.md`, `checks/`, `.reviews/`, README, execution receipts). Never stage, unstage, reset, commit or push for the review; preserve the user's index.
2. **Context.** Give each reviewer the complete diff, the scope file, the feature spec and plan, repository `AGENTS.md`/`CLAUDE.md`, `.conventions/index.md` and the selected convention sources, and the real command, exit code and output of every required check (tests, lint, format, typecheck, conventions). Missing evidence never counts as PASS. If the context budget is too small, split the scope into explicit domains, give each to its own independent agent of the same kind, and merge their reports into one report that lists every scoped file.
3. **Dispatch.** Use an independent read-only native agent with reasoning effort `high` and the caller's resolved model. Do not invoke the retired `audit` skill, Codex, a Python audit launcher or cc-hub. If native dispatch or effort `high` is unavailable, report BLOCKED; never silently skip or lower effort. Wait with `timeout=300s` in slices of at most 60 s; a timeout keeps the run BLOCKED.
4. **Report.** The reviewer modifies no file and returns JSON. Save it outside the project or under `.specs/features/<slug>/checks/`; any other file in the project is part of the diff and changes the scope:

   ```json
   {
     "schema_version": "1",
     "reviewer": {"agent": "<agent name>", "model": "<model>", "effort": "high"},
     "verdict": "PASS",
     "reviewed_files": ["<every scoped path>"],
     "checks": [{"command": "<command>", "exit_code": 0}],
     "findings": [{"severity": "warning", "file": "<path>", "line": 12, "rule": "<rule or requirement>", "evidence": "<evidence>", "correction": "<proposed correction>"}]
   }
   ```

   PASS means zero blocking finding and every check exit 0; BLOCKED needs at least one blocking finding. Warnings and info findings never block; carry them into the changelog or a follow-up.
5. **Record.** `livespec delivery review record --feature <slug> --kind combined|review|audit --report <report.json>`. The CLI stores the exact report text and its SHA-256; `verify` re-validates the stored report, so an edited receipt is refused. The CLI refuses a report whose scope changed since `prepare`, that does not list every scoped file, whose effort is not `high`, or whose verdict contradicts its findings.
6. **Corrections.** On BLOCKED, the implementing agent fixes only the blocking findings, reruns the affected checks, prepares the scope again and dispatches a fresh independent review of the complete diff. At most two correction rounds follow the initial report: the CLI then refuses another report with `round_cap_reached`, and the run stops for the maintainer with the remaining findings.
7. **Verify.** `livespec delivery review verify --feature <slug> --model <m>` exits 0 only when the latest round of every kind the lane requires passed and the diff is unchanged since; the light lane accepts the latest `combined` round or the latest `review` and `audit` rounds, and a `review` and an `audit` must come from different agents and reports (`reviewers_not_independent`). Submit `delivery_review_receipt_path` (`.specs/features/<slug>/.reviews/delivery.json`) to the goal task `delivery.review`. A later code change (for example during `/spec-test`) makes it stale: review again before the commit.

This review is independent evidence of quality. It does not replace the conventions gate, the execution certification of acceptance criteria or the visual gate.

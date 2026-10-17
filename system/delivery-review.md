<!-- @spec FR-008: End-of-feature delivery review protocol — .specs/features/086-risk-proportional-delivery/spec.md#fr-008 -->

<!-- @spec FR-004: Original root SHA and read-only review — .specs/features/096-root-feature-delivery-review/spec.md#fr-004 -->

# Delivery Review — once per feature, on the complete diff

Implementation steps run only targeted tests, lint, format and the conventions gate. Spec compliance, code quality and audit are reviewed **once**, at the end of the feature, on the complete diff. The lane decides how many independent reviewers run; the CLI decides the lane (`livespec delivery lane --feature <slug>`, with `--model <m>` unless `review_model` of `.specs/semantic/config.yaml` names the reviewer; with neither it exits 2 with `review_model_required`), never the agent. The lane reads the Quality Engineering section of the current spec and of the spec the review judged, and keeps every reason from both: editing the QE section after the review never lowers the lane. The reviewer's `qe_assessment` raises the criticality to High or contests an author High; it never contests the blast radius.

| Lane | When (CLI-verified) | End-of-feature reviewers |
|---|---|---|
| light | Low or Medium criticality (or an author High contested as Low or Medium by the current spec review, reported as `criticality_contested`), Local or Shared blast radius, no `**Delivery lane:** full`, current ready spec review | one `combined` report: spec compliance, code quality and audit |
| full | every other case, including a missing or conflicting QE classification | one `review` report (spec compliance, code quality) and one `audit` report (security, robustness, conventions), from two independent agents |

## Procedure

1. **Scope.** `livespec delivery review prepare --feature <slug> --base <rev> [--model <m>] --json`, where `<rev>` is the revision the feature started from: the commit before the one that created `.specs/features/<slug>/spec.md` (`git log --diff-filter=A --format=%H -- .specs/features/<slug>/spec.md | tail -1`, then its parent), or an older ancestor of HEAD; the creating commit itself is accepted only when it changes nothing outside the feature directory. If the spec was created in the repository root commit, pass that root commit: it identifies the logical empty state before the root. The scope then also includes every root-tree path, including bootstrap code, other specs, unchanged files and later deletions; the existing traceability exclusions still apply. Give reviewers both `git show --format= --root <base_commit>` and `git diff <base_commit>` plus untracked content so the root changes are visible. No Git object, index or history is rewritten. A newer base, or a spec that was never committed, is refused with `base_not_feature_start`, and `record` and `verify` apply the same rule to the stored base. Outside the root exception, a spec or plan change limited to lifecycle metadata (status, dates) is not part of the scope. Root spec/plan paths stay included with normalized normative identities. It hashes every path of the diff (tracked, staged or not, and untracked non-ignored files), except LiveSpec traceability files (`implementation.md`, changelogs, `progress.md`, `pipeline.md`, `checks/`, `.reviews/`, README, execution receipts). Never stage, unstage, reset, commit or push for the review; preserve the user's index.
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
7. **Verify.** While a spec revision is open (`livespec delivery revision open`, see the [review protocol](review-protocol.md)), verify is refused with `spec_revision_open`: close it first. `livespec delivery review verify --feature <slug> [--model <m>]` exits 0 only when the latest round of every kind the lane requires passed and the diff is unchanged since; the light lane accepts the latest `combined` round or the latest `review` and `audit` rounds, and a `review` and an `audit` must come from different agents and reports (`reviewers_not_independent`). Submit `delivery_review_receipt_path` (`.specs/features/<slug>/.reviews/delivery.json`) to the goal task `delivery.review`. A later code change (for example during `/spec-test`) makes it stale: review again before the commit.

This review is independent evidence of quality. It does not replace the conventions gate, the execution certification of acceptance criteria or the visual gate.

Limits the CLI cannot close: independence is declared, not proven (the CLI compares the reviewer agent names and report digests, so the caller must dispatch really distinct agents), and the receipt under `.reviews/` is local evidence, not a signature: deleting it resets the round count. An anchor-derived acceptance mapping (feature 087) is judged semantically only by this review, which `/spec-implement` requires; `/spec-fix` and `/spec-test` certify such a mapping without it, so run this review before shipping a fix whose acceptance relies on anchors.

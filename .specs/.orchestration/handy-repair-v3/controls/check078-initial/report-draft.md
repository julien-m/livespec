# Spec-code Alignment — Initial FR-004 Check

- Date: 2026-10-10; feature: 078-requirement-evidence-integrity; filter: FR-004 → AC-002, AC-004.
- Independent checker: native Codex child 01a123dc-9d40-7a41-b4f9-89a16104cd6a, runtime gpt-6.1-sol high, review budget 200000.
- Goal: 14f3dadff08cc69e609f3a2a3360c3da02e7fe2285061660bfa06d8e9ea800be; command spec-check, 39 documentary tasks, NON_VISUAL.
- Audit source/test writes: none. This report records initial gaps; it establishes no semantic readiness, mapped execution certification or whole-feature acceptance.
- Read the [immutable acceptance packet v5](/Users/julienm/projects/handy/.specs/.orchestration/handy-nine-features-01a1220e/acceptance-packet-v5.json): canonical payload SHA 853651b96cec9b630c0e2266395852bf847afb441a7a04b194ca7c980e5191e5 verified.

## Tree Validation

| Check | Observed result |
|---|---|
| System | Seven required files, three ADRs present; stack has no TBD marker; versions 21=21. |
| Feature naming | 81 directories satisfy canonical dotted-number regex; zero duplicates, invalid names, orphans. |
| Completeness |078 has required artifacts; historical038/045 changelog files absent. |
| Registry |All 81 names linked; no nonexistent feature links; 078 remains In Progress. |
| Surfaces |No surfaces.yaml or app package candidates; framework feature NON_VISUAL. |
| Structural CLI |458 files checked, 6 errors in4 files, exit1. Existing schema debt listed below. |

Read the [actual CLI output](/Users/julienm/projects/livespec/.specs/.orchestration/handy-repair-v3/controls/check078-initial/tree-validation.json) and [tree inventory](/Users/julienm/projects/livespec/.specs/.orchestration/handy-repair-v3/controls/check078-initial/tree-observations.json). The diagnostic used `livespec validate .specs --format json --no-review`; it authorizes no implementation.

## Spec and Plan Quality

| Gate | Observation |
|---|---|
| Spec stories |Five stories, each Gherkin and Mermaid flowchart. |
| Acceptance | 16 AC table rows use Given/when/then; zero clarification markers. |
| Requirements | 16 FR map ACs; four SC retained. |
| Plan |Eight steps, sequence and state diagrams, filled Constitution Check, all 16 FR referenced; database ER not applicable. |
| Implementation |Source/test mapping, progress, changelog exist; implementation.md has three existing structural errors. |

Read the [quality inventory](/Users/julienm/projects/livespec/.specs/.orchestration/handy-repair-v3/controls/check078-initial/quality-observations.json). Other FR/AC were inventoried but their implementation is outside this filtered audit.

## Functional Requirement Alignment

| FR | Status | Evidence | Gap |
|---|---|---|---|
| FR-004 | ⚠️ Partial |Canonical preparation retains complete source/model/policy context; short-name preparation fails to load the same canonical source. New goal compilation freezes the short name. |G001, G002 |

## Acceptance Alignment

| AC | Status | Evidence and limits |
|---|---|---|
| AC-002 | ⚠️ Partial |Canonical context includes 36 qualified obligations/four sources; short-name context contains zero requirements and omits the selected canonical spec. No independent new semantic review is claimed by this check. |
| AC-004 | ⚠️ Partial |Existing lifecycle/model/policy regression sources test invalidation; canonical resolution is missing at preparation/receipt lookup and new-goal freeze boundaries. No current mapped runner receipt was produced by this read-only check. |

## Reproduced Functional Gaps

### G001 — HIGH: Review lookup uses the supplied short name as the directory

Read [review_files.py](/Users/julienm/projects/livespec/validator/semantic/review_files.py) and [the actual counterexample](/Users/julienm/projects/livespec/.specs/.orchestration/handy-repair-v3/controls/check078-initial/identity-counterexample.json).

- Canonical `078-requirement-evidence-integrity`: complete=true, four sources, 36 requirements, context c85d0b3b4c3cd70b47a431ed9e53a33878eb4742067e9a4e93ba2eaec886332b.
- Short `requirement-evidence-integrity`: complete=false, three sources, zero requirements, missing_spec/unread_source, context 32aafed17af9e340d92f9eabfc4e03e46029fff7bf9fd0903d7b23a3a317a1f3.
- Receipt lookup also uses the absent short-name directory. Resolve exactly one existing confined canonical directory before preparation/lookup; preserve canonical qualified owners and context identity. Missing, ambiguous and escaping input must fail closed.

### G002 — HIGH: New immutable goals freeze the supplied short name

Read [goal_compile.py](/Users/julienm/projects/livespec/validator/goal_compile.py) and [goal_payload.py](/Users/julienm/projects/livespec/validator/goal_payload.py).

- Public `validator.goal_contracts.compile_command_goal` was called read-only with identical feature-check flags.
- Canonical input freezes078 and all expected feature bindings; goal hash 14f3dadff08cc69e609f3a2a3360c3da02e7fe2285061660bfa06d8e9ea800be.
- Short input freezes`requirement-evidence-integrity` in canonical payload and expected feature bindings; goal hash cb801dd168b65069260707bac6721d43d9840d3584f6ca662e445f9f75c17274.
- Canonicalize only new existing-feature goals before payload/hash compilation. Do not rewrite any existing immutable goal, bootstrap contract or archive. Test canonical/short equivalence, unknown/ambiguous/escape rejection and bootstrap/collection compatibility.

## Convention Compliance

| Domain | Scope | Observation | Follow-up |
|---|---|---|---|
| code |Review and goal boundary modules |Explicit typed signatures, narrow modules, no new dependencies in this audit; Python overrides JavaScript CLI rules. |Preserve these constraints during repair. |
| code/docs |Public functions in review_files.py |LOW convention gap C001:summary-only docstrings omit parameter/return/side-effect documentation required by general §24 andPython Google docstrings. |Complete public API documentation in the affected module while repairing it. |
| code/tests |Context, lifecycle, progression sources |Tests include source/model/lifecycle invalidation mechanisms; fixture judgments test mechanics only. |Run meaningful canonical-resolution positive/negative tests and independent mapped acceptance after readiness. |

Read [.conventions/index.md](/Users/julienm/projects/livespec/.conventions/index.md) and the fully loaded [Manager convention bundle](/Users/julienm/projects/handy/.specs/.orchestration/handy-nine-features-01a1220e/repair-conventions-v3.md). Exactgeneral/python/javascript/cli/stack source paths were read; architecture/logging/testing/naming were also supplied. No repo-scope convention PASS is asserted by this documentary check.

## Existing Structural Debt Outside the Selected Repair

- Feature074 changelog lacks the structural validator's required dated tagged entry; progress lacks a recognized Step table:two errors.
- Feature078 implementation lacks frontmatter and recognized Requirement Mapping/AC Mapping headings:three errors. Substantive existing mapping remains preserved.
- Feature079 implementation lacks frontmatter:one error.
- Features038/045 missing changelog files:completeness warnings.

## Suggested Fixes

- Continue `$spec-fix 078-requirement-evidence-integrity --auto --functional --fr FR-004 --model=gpt-6.1-sol --review-max-chars=200000` in the parent repair goal.
- Require genuine fresh SPEC/PLAN reviews and implement progression before source/test writes; retain model, kind, budget and source identity checks.
- Resolve existing canonical scope at review preparation/receipt lookup and at compilation of new goals; add meaningful boundary tests and update affected documentation/mappings.
- Keep trusted native Penflow persistence-source work separately owned; this initial audit makes no claim that such a source exists or is certified.

## Summary

Selected alignment:zero verified, three partial rows; two HIGH functional gaps and one LOW convention gap. Six existing structural errors remain distinct. This initial check ran no acceptance tests and modified no source/tests. Parent retains implementation.md update responsibility;`--update` was not active and no interactive metadata write was requested.

<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-001) -->
<!-- @spec(AC-001) -->

# Native Quality Engineering Analysis

LiveSpec applies this Quality Engineering context automatically for commands that create or verify quality-sensitive artifacts: `spec-specify`, `spec-plan`, and `spec-test`.

## Purpose

Quality Engineering defines what quality means for a feature, which risks must be tested, which gates must block, and which evidence proves readiness. It is a strategy and evidence contract. It is not defect hunting, implementation, audit execution, or security review.

User hooks may add local style guidance, but they cannot override native QE obligations; this file is the native LiveSpec source of truth for QE behavior.

## Quality Dimensions

| Dimension | What to decide | Evidence examples |
|---|---|---|
| Functional correctness | User-visible and system-visible behavior that must hold; AC to assertion mapping; changed branches, errors, boundaries | Gherkin-derived tests, unit or integration transcripts, AC coverage table |
| Regression risk | Nearby behavior, shared utilities, defaults, routing, parsing, serialization, state transitions | Targeted regression tests, fixture coverage, unchanged-contract proof |
| API/contract compatibility | CLI flags, request/response shape, status codes, events, files, skills, public docs | Contract tests, schema or output diff, consumer compatibility note |
| Data/migration integrity | Schema changes, backfills, idempotency, rollback, irreversible writes | Dry run, before/after sample, rollback or idempotency evidence |
| Security posture | Auth, authorization, secrets, input handling, dependency exposure, sensitive data flow | Security gate or review evidence when applicable; no vulnerability hunting here |
| Performance/scalability | Latency, throughput, memory, query shape, job volume, algorithmic complexity | Benchmark, profile, or bounded-risk rationale for affected hot paths |
| Accessibility/UX | Keyboard flow, focus, labels, contrast, responsive layout, user recovery | Screenshot proof, a11y scan, manual QA note, design acceptance |
| Observability/operability | Logs, metrics, traces, alerts, flags, runbooks, failure-mode visibility | Operational checklist, log/metric proof, rollout control note |

Mark a dimension not applicable only when the feature clearly cannot affect it.

## Risk Classification

| Field | Values | Rule |
|---|---|---|
| Criticality | Low, Medium, High | Use High when failures can block release, corrupt data, break contracts, expose security risk, or prevent core workflows. |
| Blast radius | Local, Shared, Cross-system, External | Raise blast radius when the change touches shared runtime, command defaults, global contracts, storage, auth, generated artifacts, or public docs. |
| Primary risk | Functional, Regression, Contract, Data, Security, Performance, UX, Operability | Choose the risk most likely to invalidate readiness evidence. |
| Confidence | Low, Medium, High | Confidence depends on the specificity and freshness of evidence, not on prose claims. |

## Risk-Based Test Strategy

Use the lowest reliable test level that proves the risk.

| Priority | When required | Preferred evidence |
|---|---|---|
| P0 | Critical path, shared contract, data write, security-sensitive path, release blocker | Deterministic command transcript, targeted automated test, contract proof, receipt, or artifact hash |
| P1 | Important regression or integration confidence | Focused unit/integration/e2e test, fixture coverage, compatibility note |
| P2 | Hardening, docs, exploratory confidence | Manual QA note, rendered docs proof, follow-up owner |

Prefer unit tests for pure logic, integration tests for boundaries, e2e/manual proof for cross-system or user flows, and static checks for typing/contracts/style.

## Quality Gates

| Gate | Entry criteria | Exit criteria | Blocks |
|---|---|---|---|
| Spec quality | Feature input exists and target command is `spec-specify` | Risks, expected evidence, non-functional expectations, and applicable dimensions are captured in the spec | Missing AC/FR evidence expectations or invented proof |
| Plan quality | Approved spec exists and target command is `spec-plan` | Risks map to gates, test levels, proof artifacts, and owner boundaries | No risk-to-test mapping or missing blocking gates |
| Test sufficiency | Spec/plan exist and target command is `spec-test` | Every AC/FR has sufficient test evidence or an explicit gap | Generic pass claim, missing coverage matrix, missing command transcript |
| Contract compatibility | Command/API/file/skill shape may change | Consumer-facing compatibility proof or explicit review boundary | Unproven breaking change |
| Evidence integrity | Any gate claims readiness | Real artifact, receipt, transcript, or path-backed proof exists | Prose-only proof, stale proof, unrelated proof |
| Boundary clarity | Review, audit, security, API, APEX, or test execution is adjacent | Boundary note names what belongs outside QE and where it will run | QE attempts to replace review/audit/tests |

## Evidence Contract

Every QE proof must record:

- `qe_dimensions_considered`: concrete dimension names considered for this command.
- `qe_gates_required`: blocking and non-blocking gates selected from risk.
- `qe_expected_evidence`: artifacts, transcripts, receipts, reports, or paths expected.
- `qe_gaps_or_missing_evidence`: known missing proof, or an explicit non-applicable note.
- `qe_boundary_note`: what belongs to review, security, API review, audit, APEX, or test execution rather than QE.

Evidence rows describe readiness criteria, gates, or gaps. They are not code defect findings.

## Anti-Invention Rules

- Do not mark evidence real unless an artifact, transcript, receipt, command output, hash, or path directly supports it.
- Do not treat a command name, planned test, or human confidence statement as executed proof.
- Do not replace missing proof with a generic phrase like "quality checked", "tests should pass", or "looks good".
- Do not use another feature's artifact as proof for the current feature.
- If evidence is missing, record the gap and block or mark conditional according to severity.

## Boundaries

| Surface | Boundary |
|---|---|
| Review | QE can require review when design, logic, maintainability, API, performance, or security defect hunting is needed; QE does not produce those findings. |
| Security review | QE identifies security posture as a dimension and requires security evidence when applicable; vulnerability hunting is separate. |
| API review | QE identifies contract compatibility risk; concrete API/CLI/file-format defect review is separate. |
| Audit | QE can require a broader audit when blast radius is high; audit remains the execution surface. |
| APEX | QE defines gates and evidence for APEX validation, tests, and examine phases; it does not run those phases. |
| LiveSpec tests | QE states required test evidence; `spec-test` executes and verifies tests. |

## Command Mapping

### `spec-specify`

- Enrich the spec with applicable quality dimensions, risk classification, expected proof, non-functional expectations, and explicit uncertainty.
- Add risk-oriented AC/FR wording when behavior needs evidence, but do not invent implementation proof.
- Output should make later planning able to derive gates and test levels.

### `spec-plan`

- Translate spec risks into concrete gates, test levels, proof artifacts, and command/report paths.
- Ensure implementation steps include evidence-producing tasks for P0/P1 risks.
- Record boundary notes for review, audit, security, API review, or APEX when those surfaces are required.

### `spec-test`

- Verify that AC/FR coverage has sufficient test proof for the risk level.
- Distinguish covered, partial, missing, blocked, and not-applicable proof.
- Reject generic success claims when coverage reports, command transcripts, receipts, or visual/runtime proof are required.

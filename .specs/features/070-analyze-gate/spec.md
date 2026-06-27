---
title: "Analyze Gate"
status: Implemented
priority: P1
created: 2026-06-27
updated: 2026-06-27
scope: M
number: "070"
---

# Feature Spec: Analyze Gate

- **Feature:** Analyze Gate
- **Branch:** `feature/070-analyze-gate`
- **Date:** 2026-06-27
- **Status:** Implemented
- **Input:** Analyze gate — a read-only pre-implementation cross-artifact consistency check, exposed as `spec-check --pre-impl` and as an automatic `spec-feature` phase before implementation, that detects coverage gaps and inconsistencies across spec, plan and implementation with deterministic finding IDs and CRITICAL/HIGH/MEDIUM/LOW severity, where constitution MUST violations and missing spec/plan are CRITICAL and an uncovered requirement is HIGH, and exits 1 only on CRITICAL or HIGH.
- **Feature Number:** 070

---

## User Scenarios & Testing

> Prioritize stories as P1 (critical — must ship), P2 (important — should ship), P3 (nice-to-have — can defer).

### Story 1 — Pipeline blocks implementation when artifacts disagree `P1`

**As a** developer running `/spec-feature`, **I want** a read-only gate to cross-check `spec.md` and `plan.md` after plan review and before any implementation starts, **so that** coverage gaps and constitution violations are caught before code is written, not after.

**Priority reason:** This is the gate's reason to exist. Without it, a spec whose requirements are unplanned or a plan that violates the constitution reaches the Implement phase and the cost of the gap multiplies. It is an integrated phase, not a new command.

**Independent test:** Run the analyzer on a feature directory whose `plan.md` omits one requirement present in `spec.md`; verify a HIGH coverage finding is produced and the CLI exits 1 before any implementation step.

#### Acceptance Scenarios (Gherkin — source of truth for tests)

> These Gherkin blocks are the source of truth for test scaffolding. All tests (unit, integration, E2E, visual) are derived from these scenarios, never from Mermaid diagrams.

```gherkin
Feature: Analyze gate runs read-only between plan-review and implementation
  Scenario: Gate executes after plan-review and before preflight/implement
    Given a feature whose pipeline has the plan-review phase marked done
    When the pipeline advances to the next phase
    Then the analyze phase runs before the preflight and implement phases
    And no new command surface is exposed for it

  Scenario: Analyzer never writes a file
    Given a feature directory with spec.md and plan.md
    When analyze_feature_artifacts runs against the directory
    Then it returns a report object
    And it writes no file under the feature directory
```

#### User Flow

> The Mermaid flowchart below visualizes the same flow defined in the Gherkin scenarios above.

```mermaid
flowchart TD
    A[plan-review phase done] --> B[Spawn read-only /spec-check --pre-impl]
    B --> C[analyze_feature_artifacts reads spec, plan, optional implementation]
    C --> D[Classify findings + build coverage matrix]
    D --> E{Any CRITICAL or HIGH?}
    E -- Yes --> F[Exit 1, block before preflight/implement]
    E -- No --> G[Surface MEDIUM/LOW, continue to preflight]
```

---

### Story 2 — Deterministic severity classification with stable finding IDs `P1`

**As a** spec author, **I want** the analyzer to assign CRITICAL/HIGH/MEDIUM/LOW severity by a fixed rule and to give each finding a stable ID, **so that** the same artifacts always yield the same findings with no model judgement involved.

**Priority reason:** Classification and IDs are the input to every gate decision. They must be closed-form and reproducible so the gate is testable and auditable across reruns.

**Independent test:** Run `analyze_feature_artifacts` twice on the same fixture and assert the two finding lists (IDs, severities) are identical; assert a missing `plan.md` produces a CRITICAL and an unplanned requirement produces a HIGH.

#### Acceptance Scenarios (Gherkin — source of truth for tests)

```gherkin
Feature: Deterministic severity classification across artifact checks
  Scenario: Missing required artifact is CRITICAL
    Given a feature directory missing plan.md
    When the analyzer runs
    Then it records a CRITICAL artifact finding for plan.md

  Scenario: Constitution MUST NOT violation is CRITICAL
    Given a constitution clause forbidding a phrase
    And spec.md or plan.md contains that phrase
    When the analyzer runs
    Then it records a CRITICAL constitution finding referencing constitution.md

  Scenario: Unplanned requirement is HIGH
    Given a requirement ID present in spec.md but absent from plan.md and implementation.md
    When the analyzer runs
    Then it records a HIGH coverage finding for that requirement

  Scenario: Finding IDs are deterministic and stable
    Given the same spec.md and plan.md content
    When the analyzer runs twice
    Then both runs produce identical finding IDs and severities
```

#### User Flow

```mermaid
flowchart TD
    A[Read spec, plan, optional implementation, constitution] --> B{spec.md or plan.md missing?}
    B -- Yes --> C[CRITICAL artifact finding]
    A --> D{Constitution MUST NOT phrase present in spec or plan?}
    D -- Yes --> E[CRITICAL constitution finding]
    A --> F[Scan requirement IDs in spec.md]
    F --> G{ID present in plan.md or implementation.md?}
    G -- No --> H[HIGH coverage finding]
    G -- Yes --> I[Mark covered, no finding]
    C --> J[Assign AN-CATEGORY-hash id]
    E --> J
    H --> J
```

---

### Story 3 — Coverage matrix across spec, plan and implementation `P1`

**As a** reviewer, **I want** the report to list every requirement, whether a plan task references it, and the coverage percentage, **so that** I can see at a glance which requirements are unplanned before implementation begins.

**Priority reason:** The coverage matrix turns the gate from a pass/fail switch into an actionable map of gaps, which is what lets an author fix the plan instead of guessing.

**Independent test:** Build a feature with 4 requirement IDs in `spec.md`, 3 of them referenced in `plan.md`; verify the coverage matrix marks 3 covered and 1 uncovered and reports a coverage percentage of 75.0.

#### Acceptance Scenarios (Gherkin — source of truth for tests)

```gherkin
Feature: Requirement coverage matrix and metrics
  Scenario: Requirement covered by plan is marked covered
    Given a requirement ID referenced in plan.md
    When the analyzer runs
    Then the coverage matrix marks it covered with task_refs including plan.md

  Scenario: Requirement covered only by implementation is still covered
    Given a requirement ID absent from plan.md but present in implementation.md
    When the analyzer runs
    Then the coverage matrix marks it covered with task_refs including implementation.md

  Scenario: Coverage percentage reflects covered over total
    Given 4 requirement IDs in spec.md and 3 of them referenced in plan.md
    When the analyzer runs
    Then coverage_percent equals 75.0

  Scenario: No requirements yields full coverage
    Given a spec.md with no FR/AC/SC requirement IDs
    When the analyzer runs
    Then coverage_percent equals 100.0
```

#### User Flow

```mermaid
flowchart TD
    A[Collect unique requirement IDs from spec.md] --> B[For each ID]
    B --> C{ID in plan.md?}
    C -- Yes --> D[Add plan.md ref]
    B --> E{ID in implementation.md?}
    E -- Yes --> F[Add implementation.md ref]
    D --> G[Covered]
    F --> G
    C -- No --> H{Any ref?}
    H -- No --> I[Uncovered, HIGH finding]
    G --> J[coverage_percent = covered / total * 100]
    I --> J
```

---

### Story 4 — Exit semantics and read-only guarantee `P2`

**As a** maintainer wiring the gate into CI and `/spec-feature`, **I want** the CLI to exit 1 exactly when a CRITICAL or HIGH finding exists and to never mutate the repository, **so that** the gate is a safe, idempotent precondition for implementation.

**Priority reason:** The exit code is the contract every caller depends on, and the read-only guarantee is what lets the gate run repeatedly without side effects. Getting either wrong silently breaks the pipeline.

**Independent test:** Run `livespec validate --pre-impl` on a feature with only MEDIUM/LOW findings and assert exit 0 and no files written; run it on a feature with a HIGH finding and assert exit 1; in both cases assert no `checks/`, changelog, or `src/` write occurred.

#### Acceptance Scenarios (Gherkin — source of truth for tests)

```gherkin
Feature: Exit semantics and read-only behavior
  Scenario: Exit 1 when a blocking finding exists
    Given a feature whose analysis contains a CRITICAL or HIGH finding
    When livespec validate --pre-impl runs
    Then the process exits with code 1

  Scenario: Exit 0 when only MEDIUM or LOW findings exist
    Given a feature whose analysis contains no CRITICAL or HIGH finding
    When livespec validate --pre-impl runs
    Then the process exits with code 0

  Scenario: Pre-impl mode writes nothing
    Given any feature directory
    When livespec validate --pre-impl runs
    Then no checks/ file is created
    And no changelog entry is added
    And no src/ file is modified
    And a missing implementation.md is not treated as a failure
```

#### User Flow

```mermaid
flowchart TD
    A[livespec validate --pre-impl feature] --> B[Run analyze_feature_artifacts]
    B --> C[Render report markdown or json]
    C --> D{has_blocking_findings?}
    D -- Yes --> E[Exit 1]
    D -- No --> F[Exit 0]
    B --> G[No checks/, no changelog, no src/ writes]
```

---

## Acceptance Criteria

> Each AC must be specific, testable, and verifiable. Reference them from FR below.

| ID | Criterion | Priority | Story |
|---|---|---|---|
| AC-001 | The analyze phase runs after the plan-review phase and before the preflight and implement phases as `/spec-feature` Phase 2.6, and exposes no new command surface (it reuses `/spec-check --pre-impl` → `livespec validate --pre-impl`) | P1 | Story 1 |
| AC-002 | `analyze_feature_artifacts(feature_dir, constitution_path)` reads `spec.md`, `plan.md`, optional `implementation.md`, and `constitution.md` and returns a `PreImplAnalysisReport` without writing any file | P1 | Story 1 |
| AC-003 | A missing `spec.md` or a missing `plan.md` each produce a CRITICAL `artifact` finding | P1 | Story 2 |
| AC-004 | A constitution `MUST NOT <phrase>` whose phrase appears (case-insensitively) in `spec.md` or `plan.md` produces a CRITICAL `constitution` finding located at `constitution.md` | P1 | Story 2 |
| AC-005 | A requirement ID (matching `\b(?:FR\|AC\|SC)-\d+\b`) present in `spec.md` but absent from both `plan.md` and `implementation.md` produces a HIGH `coverage` finding | P1 | Story 2 |
| AC-006 | A requirement ID present in `plan.md` or in `implementation.md` is marked covered with the corresponding `task_refs` and produces no finding | P1 | Story 3 |
| AC-007 | Each finding has a deterministic ID of the form `AN-<CATEGORY>-<8 hex>` derived from category, severity, locations and summary, stable across reruns on unchanged artifacts | P1 | Story 2 |
| AC-008 | Severity is exactly one of CRITICAL/HIGH/MEDIUM/LOW; only constitution violations and missing `spec.md`/`plan.md` are CRITICAL and only an uncovered requirement is HIGH | P1 | Story 2 |
| AC-009 | `has_blocking_findings(report)` returns True iff any finding is CRITICAL or HIGH, and the CLI exits 1 in that case and 0 otherwise | P2 | Story 4 |
| AC-010 | The report exposes a findings table, a coverage matrix, and metrics (total/covered requirements, coverage percent, critical/high counts, implementation present) rendered by both `render_report_markdown` (`## Specification Analysis Report`) and `render_report_json` | P2 | Story 3 |
| AC-011 | `--pre-impl` mode is read-only: it creates no `checks/` file, adds no changelog entry, modifies no `src/` file, and a missing `implementation.md` is not itself a failure | P2 | Story 4 |
| AC-012 | `coverage_percent` equals covered divided by total requirements times 100 rounded to 2 decimals, and equals 100.0 when there are no requirements | P2 | Story 3 |

> **Deep-link anchors:** Each AC below has a heading anchor (`#ac-001`, `#ac-002`, ...) enabling direct navigation from `implementation.md` and `@spec` comments.

### AC-001

**Criterion:** The analyze phase runs after the plan-review phase and before the preflight and implement phases as `/spec-feature` Phase 2.6, and exposes no new command surface (it reuses `/spec-check --pre-impl` → `livespec validate --pre-impl`)
**Priority:** P1 | **Story:** Story 1

### AC-002

**Criterion:** `analyze_feature_artifacts(feature_dir, constitution_path)` reads `spec.md`, `plan.md`, optional `implementation.md`, and `constitution.md` and returns a `PreImplAnalysisReport` without writing any file
**Priority:** P1 | **Story:** Story 1

### AC-003

**Criterion:** A missing `spec.md` or a missing `plan.md` each produce a CRITICAL `artifact` finding
**Priority:** P1 | **Story:** Story 2

### AC-004

**Criterion:** A constitution `MUST NOT <phrase>` whose phrase appears (case-insensitively) in `spec.md` or `plan.md` produces a CRITICAL `constitution` finding located at `constitution.md`
**Priority:** P1 | **Story:** Story 2

### AC-005

**Criterion:** A requirement ID (matching `\b(?:FR\|AC\|SC)-\d+\b`) present in `spec.md` but absent from both `plan.md` and `implementation.md` produces a HIGH `coverage` finding
**Priority:** P1 | **Story:** Story 2

### AC-006

**Criterion:** A requirement ID present in `plan.md` or in `implementation.md` is marked covered with the corresponding `task_refs` and produces no finding
**Priority:** P1 | **Story:** Story 3

### AC-007

**Criterion:** Each finding has a deterministic ID of the form `AN-<CATEGORY>-<8 hex>` derived from category, severity, locations and summary, stable across reruns on unchanged artifacts
**Priority:** P1 | **Story:** Story 2

### AC-008

**Criterion:** Severity is exactly one of CRITICAL/HIGH/MEDIUM/LOW; only constitution violations and missing `spec.md`/`plan.md` are CRITICAL and only an uncovered requirement is HIGH
**Priority:** P1 | **Story:** Story 2

### AC-009

**Criterion:** `has_blocking_findings(report)` returns True iff any finding is CRITICAL or HIGH, and the CLI exits 1 in that case and 0 otherwise
**Priority:** P2 | **Story:** Story 4

### AC-010

**Criterion:** The report exposes a findings table, a coverage matrix, and metrics (total/covered requirements, coverage percent, critical/high counts, implementation present) rendered by both `render_report_markdown` (`## Specification Analysis Report`) and `render_report_json`
**Priority:** P2 | **Story:** Story 3

### AC-011

**Criterion:** `--pre-impl` mode is read-only: it creates no `checks/` file, adds no changelog entry, modifies no `src/` file, and a missing `implementation.md` is not itself a failure
**Priority:** P2 | **Story:** Story 4

### AC-012

**Criterion:** `coverage_percent` equals covered divided by total requirements times 100 rounded to 2 decimals, and equals 100.0 when there are no requirements
**Priority:** P2 | **Story:** Story 3

---

## Functional Requirements

> Each FR must map to at least one AC. These become the rows in implementation.md.

| ID | Requirement | AC References |
|---|---|---|
| FR-001 | The system must run the analyze step as an integrated `/spec-feature` Phase 2.6 positioned after plan-review and before preflight and implement, reusing `/spec-check --pre-impl` (`livespec validate --pre-impl`) without adding a new command | AC-001, AC-011 |
| FR-002 | The system must provide `analyze_feature_artifacts(feature_dir, constitution_path)` that reads `spec.md`, `plan.md`, optional `implementation.md` and `constitution.md` and returns a `PreImplAnalysisReport` without writing any file | AC-002 |
| FR-003 | The system must emit a CRITICAL `artifact` finding for a missing `spec.md` and for a missing `plan.md` | AC-003 |
| FR-004 | The system must extract each constitution `MUST NOT <phrase>` and emit a CRITICAL `constitution` finding when the phrase appears case-insensitively in `spec.md` or `plan.md` | AC-004 |
| FR-005 | The system must collect requirement IDs from `spec.md` via the pattern `\b(?:FR\|AC\|SC)-\d+\b` and mark each covered iff its token appears in `plan.md` or `implementation.md`, emitting a HIGH `coverage` finding for each uncovered requirement | AC-005, AC-006 |
| FR-006 | The system must derive each finding ID as `AN-<CATEGORY>-<first 8 hex of sha1(category\|severity\|locations\|summary)>` so identical artifacts yield identical IDs | AC-007 |
| FR-007 | The system must restrict severity to the CRITICAL/HIGH/MEDIUM/LOW set, with CRITICAL reserved for constitution violations and missing `spec.md`/`plan.md` and HIGH reserved for an uncovered requirement | AC-008 |
| FR-008 | The system must expose `has_blocking_findings(report)` that is True iff any finding is CRITICAL or HIGH, and the `--pre-impl` CLI branch must exit 1 when it is True and 0 otherwise | AC-009 |
| FR-009 | The system must render the report as a `## Specification Analysis Report` markdown document (findings table, coverage matrix, metrics) via `render_report_markdown` and as a structured object via `render_report_json` | AC-010 |
| FR-010 | The `--pre-impl` CLI branch must be read-only: it must create no `checks/` file, add no changelog entry, modify no `src/` file, and must treat a missing `implementation.md` as non-fatal | AC-011 |
| FR-011 | The system must compute `coverage_percent` as covered over total requirements times 100 rounded to 2 decimals, defaulting to 100.0 when there are no requirements | AC-012 |

> **Deep-link anchors:** Each FR below has a heading anchor (`#fr-001`, `#fr-002`, ...) enabling direct navigation from `implementation.md` and `@spec` comments.

### FR-001

**Requirement:** The system must run the analyze step as an integrated `/spec-feature` Phase 2.6 positioned after plan-review and before preflight and implement, reusing `/spec-check --pre-impl` (`livespec validate --pre-impl`) without adding a new command
**AC References:** [AC-001](#ac-001), [AC-011](#ac-011)

### FR-002

**Requirement:** The system must provide `analyze_feature_artifacts(feature_dir, constitution_path)` that reads `spec.md`, `plan.md`, optional `implementation.md` and `constitution.md` and returns a `PreImplAnalysisReport` without writing any file
**AC References:** [AC-002](#ac-002)

### FR-003

**Requirement:** The system must emit a CRITICAL `artifact` finding for a missing `spec.md` and for a missing `plan.md`
**AC References:** [AC-003](#ac-003)

### FR-004

**Requirement:** The system must extract each constitution `MUST NOT <phrase>` and emit a CRITICAL `constitution` finding when the phrase appears case-insensitively in `spec.md` or `plan.md`
**AC References:** [AC-004](#ac-004)

### FR-005

**Requirement:** The system must collect requirement IDs from `spec.md` via the pattern `\b(?:FR\|AC\|SC)-\d+\b` and mark each covered iff its token appears in `plan.md` or `implementation.md`, emitting a HIGH `coverage` finding for each uncovered requirement
**AC References:** [AC-005](#ac-005), [AC-006](#ac-006)

### FR-006

**Requirement:** The system must derive each finding ID as `AN-<CATEGORY>-<first 8 hex of sha1(category|severity|locations|summary)>` so identical artifacts yield identical IDs
**AC References:** [AC-007](#ac-007)

### FR-007

**Requirement:** The system must restrict severity to the CRITICAL/HIGH/MEDIUM/LOW set, with CRITICAL reserved for constitution violations and missing `spec.md`/`plan.md` and HIGH reserved for an uncovered requirement
**AC References:** [AC-008](#ac-008)

### FR-008

**Requirement:** The system must expose `has_blocking_findings(report)` that is True iff any finding is CRITICAL or HIGH, and the `--pre-impl` CLI branch must exit 1 when it is True and 0 otherwise
**AC References:** [AC-009](#ac-009)

### FR-009

**Requirement:** The system must render the report as a `## Specification Analysis Report` markdown document (findings table, coverage matrix, metrics) via `render_report_markdown` and as a structured object via `render_report_json`
**AC References:** [AC-010](#ac-010)

### FR-010

**Requirement:** The `--pre-impl` CLI branch must be read-only: it must create no `checks/` file, add no changelog entry, modify no `src/` file, and must treat a missing `implementation.md` as non-fatal
**AC References:** [AC-011](#ac-011)

### FR-011

**Requirement:** The system must compute `coverage_percent` as covered over total requirements times 100 rounded to 2 decimals, defaulting to 100.0 when there are no requirements
**AC References:** [AC-012](#ac-012)

---

## Key Entities

> List the main data objects involved in this feature.

| Entity | Description | Key Fields |
|---|---|---|
| AnalyzeSeverity | The closed severity domain for findings (real `StrEnum` in `validator/pre_impl_analysis.py`) | CRITICAL, HIGH, MEDIUM, LOW |
| AnalyzeFinding | A single classified finding with a deterministic ID (real `@dataclass(frozen=True)`) | finding_id, category, severity, locations, summary, recommendation |
| RequirementCoverage | One row of the coverage matrix for a requirement ID (real `@dataclass(frozen=True)`) | requirement_id, has_plan_task, task_refs, notes |
| PreImplAnalysisReport | The complete read-only analysis result (real `@dataclass(frozen=True)`) | findings, coverage, coverage_percent, metrics |

### Classification Rules

> The severity assignment (FR-007) is closed-form. The four categories the analyzer assigns are:

| Category | Trigger | Severity |
|---|---|---|
| artifact | `spec.md` or `plan.md` missing | CRITICAL |
| constitution | a constitution `MUST NOT <phrase>` appears in spec or plan | CRITICAL |
| coverage | a `spec.md` requirement ID absent from plan and implementation | HIGH |
| (none) | a requirement ID referenced in plan or implementation | covered, no finding |

---

## Edge Cases

> Scenarios that aren't in the happy path but must be handled correctly.

- **Missing implementation.md:** Treated as non-fatal; coverage falls back to plan references only and the report's `implementation_present` metric is 0 (AC-011, FR-005).
- **No requirement IDs in spec:** `coverage_percent` defaults to 100.0 and no coverage findings are emitted (AC-012, FR-011).
- **Duplicate requirement IDs in spec:** Each ID is counted once via ordered de-duplication, so the coverage total reflects unique requirements (FR-005).
- **Empty constitution MUST NOT phrase:** A `MUST NOT` clause with no trailing phrase is skipped, never producing an empty-phrase finding (FR-004).
- **Requirement covered only by implementation.md:** Still counted as covered, with `task_refs` listing `implementation.md` (AC-006).
- **Only MEDIUM/LOW findings:** The CLI exits 0 and the warnings are surfaced without blocking the pipeline (AC-009).
- **Re-run on unchanged artifacts:** Produces byte-identical finding IDs and severities because every score is closed-form (AC-007).
- **Path is a file vs a directory:** When `--pre-impl` targets a file, the analyzer resolves its parent as the feature directory before reading artifacts (FR-001).

---

## Success Criteria

> Measurable outcomes that define when this feature is complete and successful.

| ID | Criterion | How to Measure |
|---|---|---|
| SC-001 | All P1 acceptance criteria pass automated tests | CI test suite green for `tests/test_pre_impl_analysis.py` and `tests/test_pre_impl_analysis_cli.py` |
| SC-002 | Findings and IDs are reproducible | Unit test asserting identical findings and IDs across 2 invocations on the same fixture |
| SC-003 | Exit code is 1 iff a CRITICAL or HIGH finding exists, else 0 | CLI test asserting `livespec validate --pre-impl` exit codes for blocking and non-blocking fixtures |
| SC-004 | The gate runs strictly between plan-review and preflight with no added command | Pipeline-order test asserting the `analyze` phase position and the absence of a new command entry |

---

## Clarifications

> The Clarify gate (Phase 1.6) executed on this spec during the pipeline. `rank_clarification_opportunities(scan_clarification_opportunities(spec))` returned an empty queue (0 raw opportunities): the spec contains no vague quality adjective used without a standalone numeric token, no `[NEEDS CLARIFICATION]` placeholder, and no unconfirmed `[ASSUMED]`/`TBD` marker. Per the gate's empty-queue behavior, no question was asked and no spec text was rewritten.

### Session 2026-06-27

- Clarify gate: no ambiguities — empty ranked queue (0 opportunities); pipeline continued to the plan phase without prompting.

---

*Generated by `/spec-specify` — LiveSpec v1.0*

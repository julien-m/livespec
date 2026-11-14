---
title: Review Led Delivery
priority: P1
feature: 122-review-led-delivery
status: Implemented
created: 2026-11-13
updated: 2026-11-14
---

# Feature Spec: Review Led Delivery

## Header

- **Feature:** Review Led Delivery
- **Branch:** `fix/review-led-delivery-public`
- **Date:** 2026-11-13
- **Status:** Implemented
- **Feature Number:** 122
- **Input:** Remove automatic script/certification stops from ordinary delivery and keep one independent final review. Implement this change manually, outside LiveSpec execution.

## Scope

The default skill workflow supersedes automatic certification prerequisites of earlier features for standard delivery only. Explicit historical CLI diagnostics retain their original results and contracts. Existing evidence is never rewritten. The identity122 continues the locally prepared feature; unpublished identifiers are not reallocated.

The 2026-11-14 follow-up makes useful native delegation automatic within that same delivery policy, including independent tasks/features and shared-canvas work. It adds no scheduler runtime, command or persisted state.

## User Scenarios & Testing

### Story 1 — Deliver through independent review `P1`

**Independent test:** inspect installed skills and roles, run diagnostic compatibility tests, then resume a real consumer with actual check outcomes.

```gherkin
Feature: Review led delivery
  Scenario: Administrative failure reaches review
    Given implementation is ready and an administrative script failed
    When the coordinator requests final review
    Then the independent reviewer receives the actual failure
    And missing certification does not automatically stop delivery
  Scenario: Material defect remains visible
    Given a check reveals a material product defect
    When the independent reviewer examines it
    Then the implementer corrects the defect before delivery
    And no failed or missing observation is relabeled PASS
  Scenario: Preserve existing consumers
    Given a consumer has newer private runtime fixes and historical records
    When it adopts review led delivery at a safe checkpoint
    Then those fixes and historical records are preserved
    And the coordinator reloads the new instructions explicitly
  Scenario: Ready independent work is dispatched automatically
    Given a feature has independent tasks with stable inputs and permitted native delegation
    When the coordinator starts or resumes the feature
    Then it dispatches ready workers without another opt-in
    And it coordinates shared edits and one final feature review
  Scenario: Parallelism preserves scope
    Given a plan-only request or an explicit single-agent restriction
    When the coordinator considers delegation
    Then its tasks preserve that restriction and do not start unauthorized implementation
```

```mermaid
flowchart LR
    A[Spec and plan] --> B[Implement and check]
    B --> C[Independent final review]
    C --> D[Correct material findings]
    D --> E[Deliver and report]
```

## Acceptance Criteria

### AC-001
Standard direct, nested, automatic and resumed skills use one shared short delivery policy without automatic nested goals or certification prerequisites.

### AC-002
Actual failed, unavailable and passing checks reach final review unchanged. Only concrete material findings, essential unverified behavior with material risk or missing human decisions delay delivery.

### AC-003
A fresh native reviewer examines real code, file placement, architecture, applicable conventions and results without the implementer's conversation history. It does not approve its own code changes.

### AC-004
Explicit goal diagnostics use the retained original certification inventory, fall back for unchanged skills and still reject invalid inventories.

### AC-005
Project skill projections and copied native roles resolve the shared policy correctly; old mutable agent definitions cannot reintroduce certification into the normal path.

### AC-006
The documented migration preserves consumer-specific fixes, accepted decisions, private data and historical verdicts, provides rollback and verifies the actual selected runtime.

### AC-007
Every feature automatically dispatches useful ready independent work within actual native capacity and authority. Briefs define ownership, inputs, conventions, tools and evidence; the coordinator integrates shared changes and one final review. Independent selected features in an authorized batch or program/goal/backlog may advance together, including in authorized worktrees based on actual accepted source rather than an obsolete Git HEAD. Shared pen.dev work stays in one product canvas with disjoint ownership. Indivisible tasks, missing delegation capabilities, read-only scopes, requested models/roles and actual refusals remain explicit without an agent-count gate.

## Functional Requirements

### FR-001
Replace twelve default skills and four native role prompts with the shared review-led workflow, including automatic useful delegation for every feature. Covers AC-001, AC-003, AC-005 and AC-007.

### FR-002
Preserve original command/role bodies as explicit certification diagnostics and select the archived command inventory in goal compilation. Covers AC-004.

### FR-003
Update routing, system entry points and documentation so script results inform review instead of automatically blocking progression, and ready independent work does not wait for a manual parallelism opt-in. Covers AC-001, AC-002 and AC-007.

### FR-004
Document and verify safe migration without consumer downgrade or retrospective certification. Covers AC-005 and AC-006.

## Key Entities

Initialization and migration preserve read-only previews, backed-up recovery, ordered migrations, runtime pins and historical records without creating certification prerequisites. Optional continuity is reported honestly and never required for independent feature delivery.

Existing filesystem specs, skills, role prompts and diagnostic records only; no new database or persisted state schema.

## Edge Cases

Unavailable native reviewer remains an unavailable review; missing essential product observations remain unknown. Existing read-only requests and external refusals remain binding. Existing active missions require an explicit adoption checkpoint.

## Quality Engineering

- **Criticality:** High. This changes default delivery authority and must not hide product defects or essential missing observations.
- **Blast radius:** Shared. Standard skills, native roles, diagnostics and generated Git hooks are affected; persisted historical verdicts remain intact.
- **Primary risk:** Contract. **Confidence:** Medium until public CI and the installed LiveSpec/Penflow pair are validated.
- **qe_dimensions_considered:** functional correctness, diagnostic compatibility, source/record integrity, installer packaging, custom hook preservation and safe consumer adoption. Product UI and capacity benchmarks are outside this change.
- **qe_gates_required:** One independent native final review. Script outcomes are review inputs, not automatic feature gates; material defects and missing essential observations remain explicit.
- **qe_expected_evidence:** archived-inventory regressions, generated hook behavior and ownership checks, genuine wheel installation, public CI results and observed consumer continuation.
- **qe_gaps_or_missing_evidence:** public CI, paired installation and Atlas adoption are observed. Product feature A1 rendered/native completion remains outside this tool feature and is not inferred from source review.
- **Non-functional expectations:** no added runtime dependency, no invented PASS, no consumer downgrade or history reset. Preserve custom hooks and existing data.
- **qe_boundary_note:** tools report outcomes; the final reviewer judges delivery. No new certificate chain is introduced.

## Clarifications

- The user explicitly requires manual implementation outside LiveSpec execution while retaining its feature document structure.
- The default has one final independent review; a separate plan review is only requested explicitly.
- Administrative script failures do not automatically block; a material product defect or essential observation gap remains a concrete review finding.
- Atlas reload waits for the corrected LiveSpec/Penflow pair to be validated together.

## Success Criteria

- SC-001: A standard feature reaches independent final review despite an administrative script failure.
- SC-002: Existing diagnostic compatibility checks preserve outcomes and original inventories.
- SC-003: A consumer resumes on the intended runtime without losing newer fixes or historical records.

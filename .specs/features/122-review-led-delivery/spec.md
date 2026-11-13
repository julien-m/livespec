---
title: Review Led Delivery
priority: P1
feature: 122-review-led-delivery
status: In Progress
created: 2026-11-13
updated: 2026-11-13
---

# Feature Spec: Review Led Delivery

## Header

- **Feature:** Review Led Delivery
- **Branch:** `fix/review-led-delivery-public`
- **Date:** 2026-11-13
- **Status:** In Progress
- **Feature Number:** 122
- **Input:** Remove automatic script/certification stops from ordinary delivery and keep one independent final review. Implement this change manually, outside LiveSpec execution.

## Scope

The default skill workflow supersedes automatic certification prerequisites of earlier features for standard delivery only. Explicit historical CLI diagnostics retain their original results and contracts. Existing evidence is never rewritten. The identity122 continues the locally prepared feature; unpublished identifiers are not reallocated.

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

## Functional Requirements

### FR-001
Replace ten default skills and four native role prompts with the shared review-led workflow. Covers AC-001, AC-003 and AC-005.

### FR-002
Preserve original command/role bodies as explicit certification diagnostics and select the archived command inventory in goal compilation. Covers AC-004.

### FR-003
Update routing, system entry points and documentation so script results inform review instead of automatically blocking progression. Covers AC-001 and AC-002.

### FR-004
Document and verify safe migration without consumer downgrade or retrospective certification. Covers AC-005 and AC-006.

## Key Entities

Existing filesystem specs, skills, role prompts and diagnostic records only; no new database or persisted state schema.

## Edge Cases

Unavailable native reviewer remains an unavailable review; missing essential product observations remain unknown. Existing read-only requests and external refusals remain binding. Existing active missions require an explicit adoption checkpoint.

## Success Criteria

- SC-001: A standard feature reaches independent final review despite an administrative script failure.
- SC-002: Existing diagnostic compatibility checks preserve outcomes and original inventories.
- SC-003: A consumer resumes on the intended runtime without losing newer fixes or historical records.

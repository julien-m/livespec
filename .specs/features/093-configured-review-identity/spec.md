---
title: Configured Review Identity
priority: P2
feature: 093-configured-review-identity
created: 2026-10-13
updated: 2026-10-13
status: Draft
---

# Feature Spec: Configured Review Identity

- **Feature:** review commands, goals and the delivery lane take the reviewer model and budget from `.specs/semantic/config.yaml` when no option names them
- **Feature Number:** 093
- **Branch:** `feat/lighten-delivery-gates`
- **Date:** 2026-10-13
- **Status:** Draft
- **Input:** Moved from feature 089 when the maintainer narrowed 089 to review staleness (13 October 2026). On the Handy program the reviewer model was passed by hand to every command, and a missing `--model` made goal renders fail or select another identity.

## Scope and Source Evidence

- **Observed problem:** `SemanticConfig.review_model` and `review_max_chars` exist, but goal rendering asks for `--model=` explicitly.
- **In scope:** one resolution function for model and budget used by goal rendering, progression checks and `livespec delivery lane`.
- **Out of scope:** review staleness (feature 089); the prompt and policy versions.

## User Scenarios & Testing

### Story 1 — One configuration for model and budget `P1`

**As an** agent, **I want** every review command and goal to read the reviewer model and budget from `.specs/semantic/config.yaml`, **so that** I never pass them by hand.

**Priority reason:** a missing `--model` made goal renders fail or select another identity.

**Independent test:** Render a goal and run a progression with only the configuration set.

```gherkin
Feature: Configured identity
  Scenario: Goal render without --model
    Given review_model "m1" in .specs/semantic/config.yaml
    When "livespec goal render spec-plan --feature <feature>" runs without --model
    Then the review task expects reviewer_model "m1"
```

#### User Flow

```mermaid
flowchart TD
    A[Command needs a reviewer identity] --> B{--model given?}
    B -- Yes --> C[Use it]
    B -- No --> D{review_model configured?}
    D -- Yes --> E[Use configuration]
    D -- No --> F[Exit with review_model_required]
```

## Acceptance Criteria

### AC-001

`livespec goal render`, progression checks and `livespec delivery lane` resolve the reviewer model and budget from `--model`/`--review-max-chars`, else `.specs/semantic/config.yaml`, and exit with `review_model_required` when neither names a model; for `livespec delivery lane` this replaces the 086 behavior (exit 0, lane full with `spec_review_not_current`) only for the unresolved-model case.

## Functional Requirements

- **FR-001:** One resolution function for model and budget used by goal, progression and delivery. **Maps to:** AC-001.

## Key Entities

| Entity | Description | Key Fields |
|---|---|---|
| Review identity | Resolved model and budget | model, max_chars, source |

## Edge Cases

- **Budget out of bounds in the configuration:** refused as invalid, never clamped.

## Quality Engineering

- **Risk:** Medium criticality; Shared blast radius; primary risk Contract.
- **P0 gates/evidence:** goal render and progression fixtures with and without the configuration.

## Success Criteria

| ID | Criterion | How to Measure |
|---|---|---|
| SC-001 | No review command needs `--model` when the configuration names one | Goal render and progression fixtures |

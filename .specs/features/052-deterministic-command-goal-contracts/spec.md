---
title: "Deterministic Command Goal Contracts"
status: Implemented
priority: P1
created: 2026-05-21
updated: 2026-05-21
---

# Feature 052 — Deterministic Command Goal Contracts

- **Feature Name:** Deterministic Command Goal Contracts
- **Branch:** `main`
- **Date:** 2026-05-21
- **Status:** Implemented
- **Input:** Add deterministic command goal contracts: every LiveSpec command compiles a reproducible runtime goal from machine-readable expectations, Definition of Done, flags, and resolved feature state; the generated goal is canonicalized, hashable, snapshot-tested, and used as the completion gate. The goal must be reproducible: same command, args, flags, resolved feature state, expectations, and command version produce the same goal byte-for-byte, independent of LLM wording.

## User Scenarios & Testing

### Story 1 (P1) — Command executor gets a deterministic goal before work starts

**Description:** A LiveSpec command executor needs a stable goal contract before executing a slash-command so the command objective, expected files, tests, and completion conditions are explicit and reproducible.

**Priority reason:** This prevents command drift at the start of every `/spec-*` workflow.

**Independent test:** Render the goal for `spec-feature` ten times with the same feature and flags; every canonical JSON payload and hash must match.

```gherkin
Feature: Deterministic command goal rendering
  Scenario: Same inputs produce identical goal payload and hash
    Given the builtin expectations for `spec-feature`
    And the command skill file contains a Definition of Done
    And the resolved feature is `052-deterministic-command-goal-contracts`
    And the active flags are `--auto --mono`
    When `livespec goal render spec-feature --feature 052-deterministic-command-goal-contracts --flags "--mono --auto" --json` runs ten times
    Then every response has identical canonical JSON
    And every response has the same SHA-256 goal hash
    And the normalized flags are `["--auto", "--mono"]`

  Scenario: Volatile runtime fields are excluded from the goal hash
    Given two runs happen at different wall-clock times
    When each run renders the same command goal
    Then the canonical JSON contains no timestamp
    And both hashes are identical
```

```mermaid
flowchart TD
    A[Command invocation] --> B[Normalize command name]
    B --> C[Resolve feature slug and flags]
    C --> D[Load expectations.md]
    D --> E[Extract Definition of Done from SKILL.md]
    E --> F[Build canonical goal object]
    F --> G[Stable JSON serialization]
    G --> H[SHA-256 hash]
    H --> I[Goal text for /goal slash command]
```

### Story 2 (P1) — Completion gate verifies the goal instead of trusting prose

**Description:** A LiveSpec command executor needs a deterministic final check that verifies the latest run artifact against the expectations used by the goal before reporting success.

**Priority reason:** A goal that is only rendered but not checked does not prevent incomplete command results.

**Independent test:** Run goal verification against a passing run artifact and a drifted run artifact; passing exits 0, drift exits 1, blocked exits 2.

```gherkin
Feature: Goal completion verification
  Scenario: Passing artifact satisfies the goal gate
    Given a command goal for `spec-demo`
    And a run artifact whose output satisfies all `verify.must` rules
    When `livespec goal verify spec-demo --feature 001-demo` runs
    Then the report outcome is `success`
    And the exit code is 0

  Scenario: Drifted artifact blocks completion
    Given a command goal for `spec-demo`
    And a run artifact exits 0 but misses one required marker
    When `livespec goal verify spec-demo --feature 001-demo` runs
    Then the report outcome is `drift`
    And the exit code is 1
    And the command must not report success

  Scenario: Missing artifact blocks completion
    Given no `.specs/.runs/spec-demo-*.json` artifact exists
    When `livespec goal verify spec-demo` runs
    Then the report outcome is `blocked`
    And the exit code is 2
```

```mermaid
flowchart TD
    A[Command finishing] --> B[Compile same goal again]
    B --> C[Find run artifact]
    C --> D{Artifact found?}
    D -- No --> E[blocked exit 2]
    D -- Yes --> F[Evaluate expectations verify rules]
    F --> G{Outcome}
    G -- success --> H[Allowed to report success]
    G -- drift/error --> I[Do not complete goal]
    G -- blocked --> J[Return resumable blocked status]
```

### Story 3 (P1) — All slash-command skills share the same goal protocol

**Description:** A LiveSpec maintainer needs one common command-level protocol, not twenty manually divergent snippets, so all commands use deterministic goals consistently.

**Priority reason:** The requirement is for every LiveSpec command; copy-pasted prompt prose would become inconsistent.

**Independent test:** The shared anti-drift block references `livespec goal render` at command start and `livespec goal verify` before success.

```gherkin
Feature: Shared command goal protocol
  Scenario: Anti-drift block defines the runtime goal lifecycle
    Given every builtin command imports `system/anti-drift-block.md`
    When a maintainer reads the anti-drift finalization rules
    Then the block requires goal rendering before command work starts
    And requires goal verification before success
    And explicitly forbids completing the goal on drift, blocked, or error outcomes
```

```mermaid
flowchart TD
    A[All command SKILL.md files] --> B[Import anti-drift block]
    B --> C[Runtime goal render]
    C --> D[Command-specific workflow]
    D --> E[Run artifact finalization]
    E --> F[Runtime goal verify]
```

### Story 4 (P1) — Goal carries the applicable convention domains

**Description:** A command executor needs the runtime goal to state which project conventions must be read and applied for the task, including code conventions for code/test work and design conventions for UI, mockup, visual, CSS, or screen work.

**Priority reason:** Conventions are part of the workflow contract. If they stay outside the goal, the executor can satisfy the goal while silently ignoring code or design rules.

**Independent test:** Create a fixture `.conventions/index.md` with `code` and `design-tokens` domains. Rendering a code-only goal selects `code`; rendering a UI/mockup goal selects `code` plus `design-tokens`, embeds source paths and contents in canonical JSON, and prints the selected domains in the objective.

```gherkin
Feature: Convention-aware command goals
  Scenario: Code command includes code conventions
    Given `.conventions/index.md` defines a `code` domain
    And the `code` domain references `$AIRESOURCES/code-conventions/general.md`
    When `livespec goal render spec-demo --feature 001-demo --json` runs
    Then the canonical payload contains `conventions.selected_domains[0].name = "code"`
    And the payload contains the referenced convention source path
    And the payload contains the normalized convention content and SHA-256 digest

  Scenario: UI command includes design conventions
    Given `.conventions/index.md` defines `code` and `design-tokens`
    And `.specs/features/002-ui/spec.md` mentions mockup-driven visual UI work
    When `livespec goal render spec-demo --feature 002-ui --flags "--visual" --json` runs
    Then the canonical payload contains selected domains `["code", "design-tokens"]`
    And the objective lists both selected convention domains
```

```mermaid
flowchart TD
    A[Goal compile] --> B[Read .conventions/index.md]
    B --> C[Parse domains + keywords + source refs]
    C --> D[Build deterministic task signal from command, flags, expectations, feature spec/plan]
    D --> E{Domain applies?}
    E -- code --> F[Select code domain]
    E -- UI/mockup/visual --> G[Select design domains]
    F --> H[Read source files + hash content]
    G --> H
    H --> I[Embed conventions in canonical goal payload]
```

## Acceptance Criteria

- **AC-001:** A `validator.goal_contracts` module compiles a deterministic command goal from command name, normalized flags, resolved feature, expectations metadata, verify rules, and command Definition of Done.
- **AC-002:** Canonical goal JSON serialization is stable: sorted keys, deterministic separators, normalized path strings, no timestamps, no wall-clock data, no LLM-generated wording.
- **AC-003:** Goal hashes use SHA-256 over the canonical JSON payload and are identical for identical inputs.
- **AC-004:** Flag normalization is order-independent for boolean flags and flag-value pairs.
- **AC-005:** `livespec goal render <command>` prints either human-readable goal text or JSON containing `hash`, `canonical`, and `objective`.
- **AC-006:** `livespec goal verify <command>` compiles the same goal, evaluates the run artifact through the existing expectations verifier, and exits 0 for success, 1 for drift/error, 2 for blocked.
- **AC-007:** The shared anti-drift block requires every slash command to render a deterministic goal at startup and verify it before reporting success.
- **AC-008:** Goal verification is compatible with project expectation overrides and keeps the existing total-override behavior.
- **AC-009:** Tests cover repeated rendering, flag-order independence, DoD extraction, CLI render JSON, CLI verify success, CLI verify drift, and CLI verify blocked.
- **AC-010:** Documentation maps the command goal contract to Feature 039 expectations instead of duplicating that subsystem.
- **AC-011:** If `.conventions/index.md` exists, the goal payload includes selected convention domains, source paths, source content, and SHA-256 digests.
- **AC-012:** Code convention domains are selected for command goals by default so code/test/style rules are explicit in the runtime contract.
- **AC-013:** Design convention domains are selected when command flags, expectations, or feature spec/plan mention UI, mockup, visual, CSS, screens, baselines, theme, or Penflow work.

## Functional Requirements

- **FR-001:** Provide `GoalContract` and `GoalVerification` typed data structures.
- **FR-002:** Resolve command expectations through the existing `load_expectations()` lookup path.
- **FR-003:** Extract command Definition of Done from `.agent-sync/skills/<command>/SKILL.md`.
- **FR-004:** Normalize flags deterministically, including `--flag value` to `--flag=value`.
- **FR-005:** Build a canonical JSON-safe payload with stable field order under `json.dumps(sort_keys=True, separators=(",", ":"))`.
- **FR-006:** Hash the canonical JSON with SHA-256.
- **FR-007:** Render deterministic human objective text from the canonical payload, not from LLM prose.
- **FR-008:** Add `livespec goal render`.
- **FR-009:** Add `livespec goal verify`.
- **FR-010:** Reuse `validator.verify_output.evaluate()` for completion checks.
- **FR-011:** Update shared command runtime docs so command executors know to emit exactly `/goal <rendered objective>`, check for an active goal at start (block with `/goal clear` guidance), and when to report blocked.
- **FR-012:** Preserve backwards compatibility for existing RunArtifact JSON files.
- **FR-013:** Parse `.conventions/index.md` into deterministic convention domains with keywords and `$AIRESOURCES` source references.
- **FR-014:** Select convention domains from a deterministic task signal built from command, flags, expectations, and feature `spec.md`/`plan.md`.
- **FR-015:** Embed selected convention source paths, contents, and content hashes into canonical goal JSON and list selected domains in the rendered objective.

## Key Entities

- **GoalContract:** Canonical command objective containing command, feature, normalized flags, expectations metadata, verify rules, Definition of Done, canonical JSON, and hash.
- **GoalVerification:** Completion-gate result containing the goal hash, expectations source, artifact path, verify-output outcome, exit code, and blocked reason.
- **Normalized flags:** Stable list of active flags, where ordering differences do not change the goal.
- **Convention domain:** A `.conventions/index.md` entry with a domain name, keywords, and `$AIRESOURCES` source files that must be applied for matching command goals.

## Edge Cases

- **EC-001:** Same boolean flags in different orders produce the same hash.
- **EC-002:** `--priority P1` and `--priority=P1` normalize to the same flag token.
- **EC-003:** Missing expectations file returns blocked from `goal verify`.
- **EC-004:** Malformed project override blocks and does not fall back to builtin.
- **EC-005:** Missing run artifact returns blocked.
- **EC-006:** Command without a Definition of Done still renders a goal with an empty DoD list and a warning in the objective.
- **EC-007:** Existing run artifacts without goal fields remain readable.
- **EC-008:** Missing `.conventions/index.md` renders `conventions.available = false` without blocking.
- **EC-009:** Missing convention source file still records the declared path with an empty content hash input instead of inventing rules.

## Success Criteria

- **SC-001:** Repeated render snapshot test passes for at least ten iterations.
- **SC-002:** Targeted pytest suite for goal contracts passes.
- **SC-003:** Existing expectations and verify-output tests still pass.
- **SC-004:** Shared anti-drift docs clearly gate success on deterministic goal verification.
- **SC-005:** Goal contract tests prove code and design convention domains are selected and embedded deterministically.

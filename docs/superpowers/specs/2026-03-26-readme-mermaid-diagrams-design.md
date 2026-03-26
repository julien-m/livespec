# Design: Mermaid Diagrams in README

> Add 2 Mermaid diagrams to the LiveSpec README for instant visual understanding of the framework's workflow and architecture.

**Date:** 2026-03-26
**Status:** Draft

---

## Context

The README is comprehensive (460 lines) but purely textual for process descriptions. The multi-agent architecture uses ASCII art that renders poorly. A newcomer needs to read several paragraphs before understanding how LiveSpec works.

## Goal

Add 2 Mermaid diagrams to give readers instant visual understanding:
1. **Feature Lifecycle** — how the 6 core commands chain together
2. **Multi-agent orchestration** — how `/spec.implement` delegates work

## Design

### Diagram 1: Feature Lifecycle

**Type:** `flowchart LR` (left-to-right pipeline)
**Location:** New section "How It Works" inserted between "What LiveSpec Does Differently" and "The 14 Commands"
**Content:** The 6 main commands as a linear pipeline with brief labels.

```mermaid
flowchart LR
    P["/spec.propose\nDiscover what\nto build"] --> S["/spec.specify\nWrite the spec\n(stories, AC, FR)"]
    S --> PL["/spec.plan\nTechnical plan\n(diagrams, steps)"]
    PL --> I["/spec.implement\nCode, test,\nmap to spec"]
    I --> C["/spec.check\nVerify spec\nvs code"]
    C --> E["/spec.explain\nLiving\ndocumentation"]

    style P fill:#e8f4f8,stroke:#2196F3
    style S fill:#e8f4f8,stroke:#2196F3
    style PL fill:#e8f4f8,stroke:#2196F3
    style I fill:#e8f4f8,stroke:#2196F3
    style C fill:#e8f4f8,stroke:#2196F3
    style E fill:#e8f4f8,stroke:#2196F3
```

**Design decisions:**
- No `init` in the pipeline — it's a one-time setup, not part of the feature lifecycle
- No gates/reviews shown — keeps it high-level; `/spec.feature` details are in command docs
- Multi-line labels with `\n` for readability
- Light blue fill for visual consistency

### Diagram 2: Multi-Agent Orchestration

**Type:** `flowchart TD` (top-down hierarchy)
**Location:** Replaces the ASCII art block in the existing "Multi-Agent Mode" section
**Content:** Supervisor → Superpowers (with sub-agents) + Documenter, showing the per-step cycle.

```mermaid
flowchart TD
    SUP["SUPERVISOR\n(Orchestrator / Translator)"]

    SUP -->|"Task Payload\n(FR/AC, TDD, @spec rules)"| SPW
    SUP -->|"Checkpoint\nafter each step"| DOC

    subgraph SPW ["Superpowers: Subagent-Driven Dev"]
        IMP["Implementer\n(TDD, @spec anchors)"]
        SR["Spec Reviewer\n(FR/AC coverage)"]
        QR["Quality Reviewer\n(tests + code quality)"]
        IMP --> SR --> QR
    end

    subgraph DOC ["Documenter"]
        PROG["progress.md"]
        IMPL["implementation.md"]
        CL["changelog.md"]
    end

    style SUP fill:#fff3e0,stroke:#FF9800
    style IMP fill:#e8f4f8,stroke:#2196F3
    style SR fill:#e8f4f8,stroke:#2196F3
    style QR fill:#e8f4f8,stroke:#2196F3
    style PROG fill:#f3e5f5,stroke:#9C27B0
    style IMPL fill:#f3e5f5,stroke:#9C27B0
    style CL fill:#f3e5f5,stroke:#9C27B0
```

**Design decisions:**
- Edge label on Supervisor→Superpowers shows what the Task Payload contains
- Sequential flow inside Superpowers (Implementer → Spec Reviewer → Quality Reviewer)
- Documenter shows the 3 artifacts it produces
- Color coding: orange=orchestrator, blue=execution, purple=documentation

## Changes to README.md

### Addition 1: "How It Works" section (after line 33)

Insert new section with Diagram 1 + one-liner intro + mention of `/spec.feature` shortcut.

### Modification 1: Multi-Agent Mode section (lines 367-391)

Replace the ASCII art code block with Diagram 2 in a `mermaid` fenced block.

## Out of Scope

- Diagrams in individual `commands/*.md` files
- `/spec.init` phases diagram
- `/spec.feature` pipeline with gates
- Styling changes to other README sections
